# -*- mode: ruby -*-
# vi: set ft=ruby :

##################################
##### START OF Linux SCRIPT
##################################
$ansible_engine_config = <<-SCRIPT

if ! rpm -qa | grep -q ansible
then
    yum -y install ansible ansible-lint python-pip genisoimage samba-client pywinrm
    pip install requests infoblox-client lxml ansible-vault pychef kazoo orionsdk pyvmomi pywinrm
fi

echo 'export ANSIBLE_CONFIG=/home/vagrant/ansible/group_vars/ansible.cfg' >> /home/vagrant/.bashrc

# SELinux
setenforce 0

# Openldap (for firewall)
if ! which ldapwhoami 2>&1 >/dev/null
then
    yum install -y openldap-clients
fi

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

  config.vm.define "powershell" do |powershell|
    powershell.vm.box = "mwrock/Windows2016"
    powershell.vm.hostname = "powershell"
    powershell.vm.synced_folder ".", "/powershell"
    powershell.vm.network "private_network", ip: "192.168.50.10"
    powershell.vm.provision "shell", privileged: "true", inline: $powershell_runner_config
  end

  config.vm.define "ansible" do |ansible|
    ansible.vm.box = "bento/centos-7.4"
    ansible.vm.hostname = "ansible-engine"
    ansible.vm.synced_folder "../ansible/library", "/home/vagrant/ansible/library"
    ansible.vm.synced_folder "../ansible/playbooks", "/home/vagrant/ansible/playbooks"
    ansible.vm.synced_folder "../ansible/roles", "/home/vagrant/ansible/roles"
    ansible.vm.synced_folder "./test-data", "/home/vagrant/ansible/group_vars"

    ansible.vm.provision "shell", inline: $ansible_engine_config
    ansible.vm.network "private_network", ip: "192.168.50.11"
  end
end
