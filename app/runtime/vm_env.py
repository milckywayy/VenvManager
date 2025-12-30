import os
import subprocess
import threading
import time
import uuid

from app.utils.networking import forward_port
import xml.etree.ElementTree as ET
from app.utils.vm_overlay import create_overlay, remove_overlay
from app.runtime.environment import Environment
from app.models.status import EnvStatus
import libvirt
import logging


class VMEnvException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"VMEnvException: {self.message}"


class VMEnvironment(Environment):
    def __init__(
        self,
        libvirt_client: libvirt.virConnect,
        name: str,
        display_name: str,
        template: str,
        base_image_name: str,
        internal_ports: list,
        published_ports: list,
        access_info: str,
        network_name: str,
    ):
        super().__init__(
            name, display_name, internal_ports, published_ports, access_info
        )
        self.libvirt_client = libvirt_client
        self.template = template
        self.base_image_path = os.path.join(
            os.getenv("VM_BASE_IMAGES_PATH"), base_image_name
        )
        self.network_name = network_name
        self.forwarded_ports = []

        self.image_path = f"{os.getenv('VM_OVERLAYS_PATH')}{name}.qcow2"
        create_overlay(self.base_image_path, self.image_path)

        self.domain = None
        logging.info(f"Created vm environment {self.name}")

    def _on_started(self):
        logging.debug(f"VM {self.name} booted successfully")

        for internal_port, published_port in zip(
            self.internal_ports, self.published_ports
        ):
            self.forwarded_ports.append(
                forward_port(self.ip, internal_port, published_port)
            )

    def _render_xml(self):
        required_placeholders = [
            "{{VM_NAME}}",
            "{{DISK_IMAGE}}",
            "{{VM_UUID}}",
            "{{NETWORK_NAME}}",
        ]

        xml = self.template

        missing = [ph for ph in required_placeholders if ph not in xml]
        if missing:
            logging.error(
                f"Missing placeholders in XML template for {self.name}: {missing}"
            )
            raise VMEnvException(f"XML template is missing placeholders: {missing}")
        logging.debug(
            f"All required placeholders are present in the XML template for {self.name}"
        )

        xml = xml.replace("{{VM_NAME}}", self.name)
        xml = xml.replace("{{DISK_IMAGE}}", self.image_path)
        xml = xml.replace("{{VM_UUID}}", str(uuid.uuid4()))
        xml = xml.replace("{{NETWORK_NAME}}", self.network_name)
        return xml

    def _get_ip(self) -> str | None:
        if not self.domain:
            raise VMEnvException(f"VM domain {self.name} was not created")

        try:
            xml_desc = self.domain.XMLDesc()
            root = ET.fromstring(xml_desc)

            for interface in root.findall(".//devices/interface"):
                source = interface.find("source")
                if (
                    source is not None
                    and source.attrib.get("bridge") == self.network_name
                ):
                    mac_elem = interface.find("mac")
                    if mac_elem is not None:
                        mac = mac_elem.attrib.get("address").lower()

                        output = subprocess.check_output(["ip", "neigh"]).decode()
                        for line in output.splitlines():
                            if mac in line.lower():
                                return line.split()[0]
            return None

        except Exception as e:
            raise VMEnvException(f"Failed to retrieve IP address: {e}")

    def _poll_until_booted(self):
        logging.debug(f"Waiting for VM {self.name} to finish booting...")

        timeout = int(os.getenv("VM_BOOT_TIMEOUT"))
        interval = int(os.getenv("ENV_BOOT_POLL_INTERVAL"))

        start = time.time()
        while time.time() - start < timeout:
            if self.status() != EnvStatus.BOOTING:
                logging.debug(f"VM {self.name} has booted with IP.")
                self._on_started()
                return

            time.sleep(interval)

        self.destroy()
        logging.error(
            f"VM {self.name} did not finish booting within {timeout} seconds."
        )
        raise VMEnvException(
            f"VM {self.name} did not finish booting within {timeout} seconds."
        )

    def start(self):
        try:
            xml = self._render_xml()
        except VMEnvException as e:
            logging.error(e)
            remove_overlay(self.image_path)
            raise VMEnvException(f"Failed to start VM {self.name}: {e}")

        try:
            self.domain = self.libvirt_client.defineXML(xml)
            self.domain.create()
        except libvirt.libvirtError as e:
            logging.error(f"Failed to start VM {self.name}: {e}")
            remove_overlay(self.image_path)
            raise VMEnvException(f"Failed to start VM {self.name}: {e}")

        logging.info(f"Created vm domain {self.name}")

        threading.Thread(target=self._poll_until_booted, daemon=True).start()

    def restart(self):
        if not self.domain:
            logging.error(
                f"Tried to restart domain {self.name} but domain was not created"
            )
            raise VMEnvException(f"VM domain {self.name} was not created")

        self.domain.reboot()
        logging.info(f"Restarted vm domain {self.name}")

    def status(self) -> EnvStatus:
        if not self.domain:
            return EnvStatus.UNKNOWN

        if self._get_ip() is None:
            return EnvStatus.BOOTING

        if self.ip is None:
            self.ip = self._get_ip()

        state, _ = self.domain.state()

        state_mapping = {
            libvirt.VIR_DOMAIN_NOSTATE: EnvStatus.UNKNOWN,
            libvirt.VIR_DOMAIN_RUNNING: EnvStatus.RUNNING,
            libvirt.VIR_DOMAIN_BLOCKED: EnvStatus.RUNNING,
            libvirt.VIR_DOMAIN_PAUSED: EnvStatus.PAUSED,
            libvirt.VIR_DOMAIN_SHUTDOWN: EnvStatus.PAUSED,
            libvirt.VIR_DOMAIN_SHUTOFF: EnvStatus.PAUSED,
            libvirt.VIR_DOMAIN_CRASHED: EnvStatus.UNKNOWN,
            libvirt.VIR_DOMAIN_PMSUSPENDED: EnvStatus.PAUSED,
        }

        logging.debug(f"Checking vm {self.name} status: {state}")
        return state_mapping.get(state, EnvStatus.UNKNOWN)

    def get_resource_usage(self) -> dict:
        if not getattr(self, "domain", None):
            return {"cpu": 0.0, "memory": 0, "network": {"rx": 0, "tx": 0}}

        try:
            # --- Memory (bytes) ---
            mem_stats = self.domain.memoryStats() or {}
            rss_kib = mem_stats.get("rss")
            actual_kib = mem_stats.get("actual")

            if rss_kib is not None:
                mem_bytes = int(rss_kib) * 1024
            elif actual_kib is not None:
                mem_bytes = int(actual_kib) * 1024
            else:
                try:
                    info = self.domain.info()
                    mem_bytes = int(info[2]) * 1024
                except Exception:
                    mem_bytes = 0

            # --- Network (bytes) ---
            rx_total = tx_total = 0
            try:
                xml_desc = self.domain.XMLDesc()
                root = ET.fromstring(xml_desc)
                for target in root.findall(".//devices/interface/target"):
                    dev = target.attrib.get("dev")
                    if not dev:
                        continue
                    try:
                        stats = self.domain.interfaceStats(dev)
                        rx_total += int(stats[0] or 0)
                        tx_total += int(stats[4] or 0)
                    except Exception:
                        continue
            except Exception:
                pass

            return {
                "memory": int(mem_bytes),
                "network": {"rx": int(rx_total), "tx": int(tx_total)},
            }

        except Exception as e:
            logging.exception(
                f"Failed to read VM resources for {getattr(self, 'name', 'unknown')}: {e}"
            )
            return {"cpu": 0.0, "memory": 0, "network": {"rx": 0, "tx": 0}}

    def destroy(self):
        if not self.domain:
            logging.warning(
                f"Tried to destroy domain {self.name} but domain was not created"
            )
            return

        for forwarded_port in self.forwarded_ports:
            forwarded_port.terminate()

        self.domain.destroy()
        self.domain.undefine()
        remove_overlay(self.image_path)
        logging.info(f"Removed vm environment {self.name}")
