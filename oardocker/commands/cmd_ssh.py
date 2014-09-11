import time
import os
import click
from oardocker.cli import pass_context, pass_state
from oardocker.utils import touch, check_tcp_port_open


@click.command('ssh')
@click.argument('hostname', required=False, default="frontend")
@pass_state
@pass_context
def cli(ctx, state, hostname):
    """Connect to machine via SSH."""
    touch(ctx.ssh_config)
    node_name = ''.join([i for i in hostname if not i.isdigit()])
    nodes = ("frontend", "services", "node", "server")
    if not node_name in nodes:
        raise click.ClickException("Cannot find the container with the name "
                                   "'%s'" % hostname)
    containers = dict((c.hostname, c) for c in ctx.get_containers(state))
    if not hostname in containers.keys():
        raise click.ClickException("The container must be started before "
                                   "running this command. Run  `oardocker"
                                   " start` first")
    ipaddress = containers[hostname].ip
    if not check_tcp_port_open(ipaddress, 22):
        click.echo("Waiting ssh to be available for '%s'" % hostname, nl=False)
        while not check_tcp_port_open(ipaddress, 22):
            time.sleep(1)
            click.echo(".", nl=False)
        click.echo("")
    os.system('ssh -F %s %s' % (ctx.ssh_config, hostname))