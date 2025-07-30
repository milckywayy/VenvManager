from environment import Environment
from app.model.status import EnvStatus
import libvirt

libvirt_client = libvirt.open('qemu:///system')


class VMEnvironment(Environment):
    def __init__(
            self, name: str,
            template_path: str,
            exposed_ports: list,
            host_ports: list,
            args: dict
    ):
        super().__init__(name, exposed_ports, host_ports, args)
        self.template_path = template_path

        self.domain = None

    def _load_template(self):
        with open(self.template_path, "r") as f:
            return f.read()

    def _render_xml(self):
        xml = self._load_template()
        xml = xml.replace("{{VM_NAME}}", self.name)
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


if __name__ == "__main__":
    vm = VMEnvironment(
        name="ctf-vm01",
        template_path="/home/milckywayy/PycharmProjects/VenvManager/temp/vm_template.xml",
        exposed_ports=[22],
        host_ports=[10022],
        args={'FLAG': 'TEST123'}
    )

    vm.start()
    print(f"Status: {vm.status()}")
    print(f"Access info: {vm.get_access_info()}")

    input("Naciśnij Enter aby zatrzymać vm...")
    vm.destroy()