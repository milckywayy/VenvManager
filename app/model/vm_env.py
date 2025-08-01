import uuid
from app.utils.networking import get_bridge_name
from app.utils.vm_overlay import create_overlay, remove_overlay
from environment import Environment
from app.config import Config
from app.model.status import EnvStatus
import libvirt
import logging

libvirt_client = libvirt.open('qemu:///system')


class VMEnvException(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return f"VMEnvException: {self.message}"


class VMEnvironment(Environment):
    def __init__(
            self, name: str,
            template_path: str,
            base_image_path: str,
            internal_ports: list,
            published_ports: list,
            network_name: str,
            args: dict
    ):
        super().__init__(name, internal_ports, published_ports, args)
        self.template_path = template_path
        self.base_image_path = base_image_path
        self.network_name = network_name

        Config.OVERLAY_PATH.mkdir(parents=True, exist_ok=True)
        self.image_path = str(Config.OVERLAY_PATH / f"{name}.qcow2")

        create_overlay(base_image_path, self.image_path)

        self.domain = None
        logging.info(f"Created vm environment {self.name}")


    def _load_template(self):
        logging.debug(f"Loading template for {self.name} from {self.template_path}")
        with open(self.template_path, "r") as f:
            return f.read()

    def _render_xml(self):
        required_placeholders = [
            "{{VM_NAME}}",
            "{{DISK_IMAGE}}",
            "{{VM_UUID}}",
            "{{NETWORK_NAME}}"
        ]

        xml = self._load_template()

        missing = [ph for ph in required_placeholders if ph not in xml]
        if missing:
            logging.error(f"Missing placeholders in XML template for {self.name}: {missing}")
            raise VMEnvException(f"XML template is missing placeholders: {missing}")
        logging.debug(f"All required placeholders are present in the XML template for {self.name}")

        xml = xml.replace("{{VM_NAME}}", self.name)
        xml = xml.replace("{{DISK_IMAGE}}", self.image_path)
        xml = xml.replace("{{VM_UUID}}", str(uuid.uuid4()))
        xml = xml.replace("{{NETWORK_NAME}}", self.network_name)
        return xml

    def start(self):
        try:
            xml = self._render_xml()
        except VMEnvException as e:
            logging.error(e)
            remove_overlay(self.image_path)
            raise VMEnvException(f"Failed to start VM {self.name}: {e}")

        try:
            self.domain = libvirt_client.defineXML(xml)
            self.domain.create()
        except libvirt.libvirtError as e:
            logging.error(f"Failed to start VM {self.name}: {e}")
            remove_overlay(self.image_path)
            raise VMEnvException(f"Failed to start VM {self.name}: {e}")

        logging.info(f"Created vm domain {self.name}")

    def on_started(self):
        pass

    def stop(self):
        if not self.domain:
            logging.error(f"Tried to stop domain {self.name} but domain was not created")
            raise VMEnvException(f"VM domain {self.name} was not created")

        self.domain.shutdown()
        logging.info(f"Stopped vm domain {self.name}")

    def restart(self):
        if not self.domain:
            logging.error(f"Tried to restart domain {self.name} but domain was not created")
            raise VMEnvException(f"VM domain {self.name} was not created")

        self.domain.reboot()
        logging.info(f"Restarted vm domain {self.name}")

    def status(self) -> EnvStatus:
        if not self.domain:
            return EnvStatus.UNKNOWN

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

    def get_access_info(self) -> dict:
        return {}

    def destroy(self):
        if not self.domain:
            logging.warning(f"Tried to destroy domain {self.name} but domain was not created")
            return

        self.domain.destroy()
        self.domain.undefine()
        remove_overlay(self.image_path)
        logging.info(f"Removed vm environment {self.name}")


if __name__ == "__main__":
    cluster_id = 5
    network_name = get_bridge_name(cluster_id)

    vm1 = VMEnvironment(
        name="ctf-vm01",
        template_path="/home/milckywayy/PycharmProjects/VenvManager/temp/vm_template.xml",
        base_image_path="/var/lib/libvirt/images/ubuntu18.04.qcow2",
        internal_ports=[22],
        published_ports=[10022],
        network_name=network_name,
        args={'FLAG': 'TEST123'}
    )

    vm2 = VMEnvironment(
        name="ctf-vm02",
        template_path="/home/milckywayy/PycharmProjects/VenvManager/temp/vm_template.xml",
        base_image_path="/var/lib/libvirt/images/ubuntu18.04.qcow2",
        internal_ports=[22],
        published_ports=[10023],
        network_name=network_name,
        args={'FLAG': 'TEST123'}
    )

    vm1.start()
    vm2.start()
    print(f"Status: {vm1.status()}")
    print(f"Status: {vm2.status()}")

    input("Naciśnij Enter aby zatrzymać vm...")
    vm1.destroy()
    vm2.destroy()