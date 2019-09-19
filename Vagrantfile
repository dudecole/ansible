# -*- mode: ruby -*-
# vi: set ft=ruby :

##################################
##### START OF Ansible Engine SCRIPT
##################################
$ansible_engine_config = <<-SCRIPT

# check if ansible is installed
if ! rpm -qa | grep -q ansible
then
    yum -y install ansible ansible-lint python3-pip genisoimage samba-client
    pip3 install requests infoblox-client lxml ansible-vault pychef kazoo orionsdk pyvmomi pywinrm
fi

# set ansible_config path
echo 'export ANSIBLE_CONFIG=/home/vagrant/ansible/group_vars/ansible.cfg' >> /home/vagrant/.bashrc

# Disable SELinux
setenforce 0

SCRIPT
##################################
## END OF Linux SCRIPT
##################################


##################################
##### START OF CentOS vanilla SCRIPT
##################################
$centos_config = <<-SCRIPT

# SELinux
setenforce 0

SCRIPT
##################################
## END OF Linux SCRIPT
##################################


##################################
## START OF WINDOWS SCRIPT
##################################
$powershell_runner_config = <<-SCRIPT

# disable the windows firewall
netsh advfirewall set allprofiles state off

# install the powercli module
Save-Module -Name VMware.PowerCLI -Path "c:\\Windows\\System32\\WindowsPowerShell\\v1.0\\Modules"

# disable hibernation
powercfg /hibernate off

# setting power settings
powercfg.exe -SETACTIVE 8c5e7fda-e8bf-4a96-9a85-a6e23a8c635c

# extend the eval license for windows (causes reboots if not)
slmgr.vbs /rearm

SCRIPT
##################################
## END OF Windows SCRIPT
##################################


##################################
# vagrant configuration
##################################
Vagrant.configure("2") do |config|

  config.vm.define "ansible" do |ansible|
    ansible.vm.box = "bento/centos-7.4"
    ansible.vm.hostname = "ansible"
    ansible.vm.synced_folder "../ix-rancher-setup/library", "/home/vagrant/ansible/library"
    ansible.vm.synced_folder "../ix-rancher-setup/playbooks", "/home/vagrant/ansible/playbooks"
    ansible.vm.synced_folder "../ix-rancher-setup/roles", "/home/vagrant/ansible/roles"
    ansible.vm.synced_folder "../ix-rancher-setup/group_vars", "/home/vagrant/ansible/group_vars"
    ansible.vm.provision "shell", inline: $ansible_engine_config
    ansible.vm.network "private_network", ip: "192.168.50.10"
  end

  config.vm.define "centos1" do |centos1|
    centos1.vm.box = "bento/centos-7.4"
    centos1.vm.hostname = "centos1"
    centos1.vm.provision "shell", inline: $centos_config
    centos1.vm.network "private_network", ip: "192.168.50.11"
  end

    config.vm.define "centos2" do |centos2|
    centos2.vm.box = "bento/centos-7.4"
    centos2.vm.hostname = "centos2"
    centos2.vm.provision "shell", inline: $centos_config
    centos2.vm.network "private_network", ip: "192.168.50.12"
  end

  config.vm.define "centos3" do |centos3|
    centos3.vm.box = "bento/centos-7.4"
    centos3.vm.hostname = "centos3"
    centos3.vm.provision "shell", inline: $centos_config
    centos3.vm.network "private_network", ip: "192.168.50.13"
  end

  config.vm.define "windows" do |windows|
    windows.vm.box = "mwrock/Windows2016"
    windows.vm.hostname = "windows"
#   windows.vm.synced_folder ".", "/powershell"
    windows.vm.network "private_network", ip: "192.168.50.14"
    windows.vm.provision "shell", privileged: "true", inline: $powershell_runner_config
  end
end