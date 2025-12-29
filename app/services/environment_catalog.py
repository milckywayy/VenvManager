from __future__ import annotations
import xml.etree.ElementTree as ET


class EnvironmentCatalog:
    def __init__(self, *, docker_client, libvirt_client):
        self.docker_client = docker_client
        self.libvirt_client = libvirt_client

    def list_docker_image_tags(self) -> list[str]:
        images = self.docker_client.images.list()
        tags: list[str] = []
        for img in images:
            for tag in getattr(img, "tags", []) or []:
                tags.append(tag)
        return sorted(set(tags))

    def list_vm_images(self) -> dict[str, str]:
        out: dict[str, str] = {}
        for name in self.libvirt_client.listDefinedDomains():
            dom = self.libvirt_client.lookupByName(name)
            xml = dom.XMLDesc()
            tree = ET.fromstring(xml)

            for disk in tree.findall("./devices/disk"):
                if disk.get("device") != "disk":
                    continue
                source = disk.find("source")
                if source is not None and "file" in source.attrib:
                    out[name] = source.get("file")
                    break
        return out
