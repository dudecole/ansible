# Dudes Ansible Repo


This repo contains Ansible-related configuration files and code, including the
Custom Python-Ansible modules.

## Run tests

1.  Run `vagrant up` from within this repository:

        vagrant up

    The first time you run this it should take around 2 minutes since it has to download a slim CentOS 7 VM image. Once the image has been downloaded, all subsequent "vagrant up" commands should take around 20-30 seconds on a decent machine.

2.  Connect to the Ansible engine/runtime VM:

        vagrant ssh ansible

3.  Test your playbooks:

        ansible-lint playbooks/<playbook.yml>

4.  Run your playbooks:

        ansible-playbook playbooks/<playbook.yml>

5.  When you're done just `exit`.


## Manage the Vagrant VM
1.  If you make changes to any of the Ansible code and would like to refresh the Vagrant VM before connecting to it again for more testing:

        vagrant provision --provision-with file

2.  If you want to preserve the VM as is for future testing, but free up the VM resources:

        vagrant halt

3.  If you're done with testing in the VM and don't mind re-provisioning when you need to test again:

        vagrant destroy


## Get the software

Official Git, VirtualBox, and Vagrant are required to test Ansible in the above workflow.  Git has an SSH client bundled, which Vagrant uses for connecting and uploading files to the VM.  If you'd prefer to use PuTTY,
- Git:  `https://git-scm.com/downloads`
- VirtualBox:  `https://www.virtualbox.org/wiki/Downloads`
- Vagrant:  `https://www.vagrantup.com/downloads.html`

Git has an SSH client bundled, which Vagrant uses for connecting to and uploading files to the Vagrant VM.  If you'd prefer to use PuTTY, get it here:
`https://www.chiark.greenend.org.uk/~sgtatham/putty/latest.html`
And here's a great how-to for setting it up:
`https://howtoprogram.xyz/2016/10/22/run-vagrant-ssh-windows/`


### Install Vagrant
1.  Install vagrant from here: https://www.vagrantup.com/downloads.html .
    Please do not use the software center, it has an old version.
2.  Make sure `vagrant.exe` can be found on your PATH, this may require
    changes to the PATH variable. To test, run `get-command vagrant` in a
    powershell prompt.
    1.  Make sure to close whatever terminal you were using and open it again
        whenever the PATH is changed to pick up changes to that variable.


## What If Something Goes Wrong

Talk to: dudecole@outlook.com
