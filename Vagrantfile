Vagrant.configure("2") do |config|
  config.vm.box = "bento/ubuntu-20.04"

  config.vm.provider "virtualbox" do |v|
    v.memory = 4096
    v.cpus = 1
  end

  # config.vm.provision "shell", path: "scripts/provision-common.sh"

  config.vm.define "provider", primary: true do |c|
    c.vm.hostname = "provider"
    # c.vm.provision "shell", path: "scripts/provision-provider.sh"
  end

  # config.vm.define "consumer" do |c|
  #   c.vm.hostname = "consumer"
  #   c.vm.provision "shell", path: "scripts/provision-consumer.sh"
  # end
end