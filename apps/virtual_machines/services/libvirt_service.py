"""
Сервис для работы с KVM-гипервизором через libvirt.
Используется как контекстный менеджер: with LibvirtService(...) as svc: ...
"""
import uuid
import logging
import subprocess
from typing import Optional

logger = logging.getLogger(__name__)

try:
    import libvirt
    LIBVIRT_AVAILABLE = True
except ImportError:
    LIBVIRT_AVAILABLE = False
    logger.warning("libvirt-python не установлен — используется mock-режим")


class LibvirtService:
    OS_XML = {
        'ubuntu-22.04': 'linux',
        'ubuntu-20.04': 'linux',
        'debian-12':    'linux',
        'centos-9':     'linux',
        'rocky-9':      'linux',
        'windows-2022': 'windows',
    }

    def __init__(self, host: str, port: int = 16509):
        self.host = host
        self.port = port
        self.uri = f"qemu+tcp://{host}:{port}/system"
        self._conn = None

    def __enter__(self):
        if not LIBVIRT_AVAILABLE:
            logger.warning("libvirt не доступен, используем mock")
            return self
        self._conn = libvirt.open(self.uri)
        if not self._conn:
            raise ConnectionError(f"Не удалось подключиться к гипервизору: {self.uri}")
        return self

    def __exit__(self, *args):
        if self._conn:
            try:
                self._conn.close()
            except Exception:
                pass
        self._conn = None

    def _build_domain_xml(
        self,
        name: str,
        vm_uuid: str,
        vcpus: int,
        ram_mb: int,
        disk_path: str,
        os_type: str,
    ) -> str:
        ram_kb = ram_mb * 1024
        os_variant = self.OS_XML.get(os_type, 'linux')
        return f"""<domain type='kvm'>
  <name>{name}</name>
  <uuid>{vm_uuid}</uuid>
  <memory unit='KiB'>{ram_kb}</memory>
  <currentMemory unit='KiB'>{ram_kb}</currentMemory>
  <vcpu placement='static'>{vcpus}</vcpu>
  <os>
    <type arch='x86_64' machine='pc-q35-7.2'>hvm</type>
    <boot dev='hd'/>
  </os>
  <features><acpi/><apic/><vmport state='off'/></features>
  <cpu mode='host-passthrough' check='none' migratable='on'/>
  <clock offset='utc'>
    <timer name='rtc' tickpolicy='catchup'/>
    <timer name='pit' tickpolicy='delay'/>
    <timer name='hpet' present='no'/>
  </clock>
  <devices>
    <emulator>/usr/bin/qemu-system-x86_64</emulator>
    <disk type='file' device='disk'>
      <driver name='qemu' type='qcow2' discard='unmap'/>
      <source file='{disk_path}'/>
      <target dev='vda' bus='virtio'/>
    </disk>
    <interface type='network'>
      <source network='default'/>
      <model type='virtio'/>
    </interface>
    <serial type='pty'><target port='0'/></serial>
    <console type='pty'><target type='serial' port='0'/></console>
    <graphics type='vnc' port='-1' autoport='yes' listen='127.0.0.1'/>
    <video><model type='virtio' heads='1'/></video>
    <memballoon model='virtio'/>
    <rng model='virtio'><backend model='random'>/dev/urandom</backend></rng>
  </devices>
</domain>"""

    def create_vm(
        self,
        name: str,
        vcpus: int,
        ram_mb: int,
        disk_gb: int,
        os_type: str,
        disk_base_path: str,
    ) -> str:
        """Создаёт VM, возвращает libvirt UUID."""
        vm_uuid = str(uuid.uuid4())
        disk_path = f"{disk_base_path}/{vm_uuid}.qcow2"

        if not LIBVIRT_AVAILABLE:
            logger.info(f"[MOCK] create_vm name={name} uuid={vm_uuid}")
            return vm_uuid

        # Создаём диск
        subprocess.run(
            ['qemu-img', 'create', '-f', 'qcow2', disk_path, f'{disk_gb}G'],
            check=True, capture_output=True,
        )

        xml = self._build_domain_xml(name, vm_uuid, vcpus, ram_mb, disk_path, os_type)
        domain = self._conn.defineXML(xml)
        domain.create()
        logger.info(f"Created VM {name} uuid={vm_uuid} on {self.host}")
        return vm_uuid

    def stop_vm(self, libvirt_uuid: str):
        if not LIBVIRT_AVAILABLE:
            logger.info(f"[MOCK] stop_vm {libvirt_uuid}")
            return
        domain = self._conn.lookupByUUIDString(libvirt_uuid)
        domain.shutdown()

    def force_stop_vm(self, libvirt_uuid: str):
        if not LIBVIRT_AVAILABLE:
            return
        domain = self._conn.lookupByUUIDString(libvirt_uuid)
        domain.destroy()

    def start_vm(self, libvirt_uuid: str):
        if not LIBVIRT_AVAILABLE:
            logger.info(f"[MOCK] start_vm {libvirt_uuid}")
            return
        domain = self._conn.lookupByUUIDString(libvirt_uuid)
        domain.create()

    def reboot_vm(self, libvirt_uuid: str):
        if not LIBVIRT_AVAILABLE:
            return
        domain = self._conn.lookupByUUIDString(libvirt_uuid)
        domain.reboot()

    def delete_vm(self, libvirt_uuid: str, disk_path: Optional[str] = None):
        if not LIBVIRT_AVAILABLE:
            logger.info(f"[MOCK] delete_vm {libvirt_uuid}")
            return
        try:
            domain = self._conn.lookupByUUIDString(libvirt_uuid)
            try:
                domain.destroy()
            except Exception:
                pass
            domain.undefineFlags(
                libvirt.VIR_DOMAIN_UNDEFINE_MANAGED_SAVE
                | libvirt.VIR_DOMAIN_UNDEFINE_SNAPSHOTS_METADATA
            )
        except libvirt.libvirtError as e:
            logger.warning(f"libvirt delete error for {libvirt_uuid}: {e}")

        if disk_path:
            import os
            if os.path.exists(disk_path):
                os.remove(disk_path)
                logger.info(f"Deleted disk {disk_path}")

    def get_vm_status(self, libvirt_uuid: str) -> str:
        if not LIBVIRT_AVAILABLE:
            return 'running'
        try:
            domain = self._conn.lookupByUUIDString(libvirt_uuid)
            state, _ = domain.state()
            return {
                libvirt.VIR_DOMAIN_RUNNING:  'running',
                libvirt.VIR_DOMAIN_PAUSED:   'paused',
                libvirt.VIR_DOMAIN_SHUTOFF:  'stopped',
                libvirt.VIR_DOMAIN_CRASHED:  'error',
                libvirt.VIR_DOMAIN_PMSUSPENDED: 'paused',
            }.get(state, 'unknown')
        except Exception:
            return 'error'

    def get_node_stats(self) -> dict:
        """Статистика физического узла для обновления Hypervisor.used_*."""
        if not LIBVIRT_AVAILABLE:
            return {'used_vcpus': 0, 'used_ram_mb': 0}
        node_info = self._conn.getNodeInfo()
        # node_info[2] = total CPUs, getFreeCPUs недоступен напрямую — считаем через домены
        used_vcpus = sum(
            d.vcpusFlags(libvirt.VIR_DOMAIN_VCPU_MAXIMUM)
            for d in self._conn.listAllDomains(libvirt.VIR_CONNECT_LIST_DOMAINS_ACTIVE)
        )
        free_mem_kb = self._conn.getFreeMemory() // 1024
        total_mem_kb = node_info[1] * 1024
        used_mem_mb = (total_mem_kb - free_mem_kb) // 1024
        return {'used_vcpus': used_vcpus, 'used_ram_mb': max(0, used_mem_mb)}
