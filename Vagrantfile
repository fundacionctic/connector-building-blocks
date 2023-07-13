Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-20.04"

  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 1
  end

  config.vm.provision "shell", path: "scripts/provision-common.sh"

  # Install Avahi to enable mDNS resolution between boxes
  # https://stackoverflow.com/a/30780347
  config.vm.provision "allow_guest_host_resolution",
  type: "shell",
  inline: <<-SHELL
    apt-get update -y
    apt-get install -y avahi-daemon libnss-mdns
  SHELL

  # The provider must be provisioned before the consumer
  config.vm.define "provider", primary: true do |c|
    c.vm.hostname = "provider"
    c.vm.provision "shell", path: "scripts/provision-provider.sh"
    c.vm.network "private_network", type: "dhcp"
  end

  config.vm.define "consumer" do |c|
    c.vm.hostname = "consumer"
    c.vm.provision "shell", path: "scripts/provision-consumer.sh"
    c.vm.network "private_network", type: "dhcp"
    c.vm.network "forwarded_port", guest: 15672, host: 30200
  end
  
  config.vm.define "keycloak" do |c|
    c.vm.hostname = "keycloak"

    # This is a quick and dirty fix to avoid issues with 
    # the "iat" claim validation in the EDC connector.
    c.vm.provision "shell", inline: <<-SHELL
      set -ex
      tm=$(python3 -c "import datetime; now = datetime.datetime.now(); ago = now - datetime.timedelta(seconds=2); print(ago);") \
      && timedatectl set-time "$tm"
    SHELL

    c.vm.provision "shell", path: "scripts/provision-keycloak.sh"
    c.vm.network "private_network", type: "dhcp"
    c.vm.network "forwarded_port", guest: 8080, host: 30100
  end
end