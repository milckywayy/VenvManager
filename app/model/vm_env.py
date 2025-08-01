import uuid
from app.utils.networking import get_bridge_name
from app.utils.vm_overlay import create_overlay, remove_overlay
from environment import Environment
from app.config import Config
from app.model.status import EnvStatus
import libvirt

libvirt_client = libvirt.open('qemu:///system')


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


    def _load_template(self):
        with open(self.template_path, "r") as f:
            return f.read()

    def _render_xml(self):
        xml = self._load_template()
        xml = xml.replace("{{VM_NAME}}", self.name)
        xml = xml.replace("{{DISK_IMAGE}}", self.image_path)
        xml = xml.replace("{{VM_UUID}}", str(uuid.uuid4()))
        xml = xml.replace("{{NETWORK_NAME}}", self.network_name)
        return xml

    def start(self):
        xml = self._render_xml()
        self.domain = libvirt_client.defineXML(xml)
        self.domain.create()

    def on_started(self):
        pass

    def stop(self):
        self.domain.shutdown()

    def restart(self):
        self.domain.reboot()

    def status(self) -> EnvStatus:
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

        return state_mapping.get(state, EnvStatus.UNKNOWN)

    def get_access_info(self) -> dict:
        return {}

    def destroy(self):
        self.domain.destroy()
        self.domain.undefine()
        remove_overlay(self.image_path)


if __name__ == "__main__":
    cluster_id = 100
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