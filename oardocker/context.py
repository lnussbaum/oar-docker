import os
import os.path as op
import sys
import click

from io import open
from functools import update_wrapper

from .state import State
from .client import Docker
from .compat import basestring


CONTEXT_SETTINGS = dict(auto_envvar_prefix='oardocker',
                        help_option_names=['-h', '--help'])


class Context(object):

    def __init__(self):
        self.current_dir = os.getcwd()
        self.verbose = False
        self.workdir = self.current_dir
        self.cgroup_path = None
        # oar archive url
        self.oar_website = "http://oar-ftp.imag.fr/oar/2.5/sources/stable"
        self.oar_tarball = "%s/oar-2.5.3.tar.gz" % self.oar_website
        self.prefix = "oardocker"

    @property
    def env(self):
        with open(self.env_file) as env_file:
            return env_file.read().strip()

    def image_name(self, node, tag=""):
        if not tag == "":
            tag = ":%s" % tag
        if not self.env == "default":
            return "%s/%s-%s%s" % (self.prefix, self.env, node, tag)
        else:
            return "%s/%s%s" % (self.prefix, node, tag)

    @property
    def state(self):
        if not hasattr(self, '_state'):
            self._state = State(self,
                                state_file=self.state_file,
                                dns_file=self.dns_file)
        return self._state

    def update(self):
        self.envdir = op.join(self.workdir, ".%s" % self.prefix)
        self.postinstall_dir = op.join(self.envdir, "postinstall")
        self.env_file = op.join(self.envdir, "env")
        self.state_file = op.join(self.envdir, "state.json")
        self.dns_file = op.join(self.envdir, "dnsmasq.d", "hosts")
        self.docker = Docker(self, self.docker_host, self.docker_binary)

    def assert_valid_env(self):
        if not os.path.isdir(self.envdir):
            raise click.ClickException("Missing oardocker env directory."
                                       " Run `oardocker init` to create"
                                       " a new oardocker environment")

    def log(self, msg, *args, **kwargs):
        """Logs a message to stderr."""
        if args:
            msg %= args
        kwargs.setdefault("file", sys.stderr)
        click.echo(msg, **kwargs)

    def vlog(self, msg, *args):
        """Logs a message to stderr only if verbose is enabled."""
        if self.verbose:
            self.log(msg, *args)


pass_context = click.make_pass_decorator(Context, ensure=True)


class deprecated_cmd(object):
    """This is a decorator which can be used to mark cmd as deprecated. It will
    result in a warning being emmitted when the command is invoked."""

    def __init__(self, message=""):
        if message:
            self.message = "%s." % message
        else:
            self.message = message

    def __call__(self, f):

        @click.pass_context
        def new_func(ctx, *args, **kwargs):
            msg = click.style("warning: `%s` command is deprecated. %s" %
                              (ctx.info_name, self.message), fg="yellow")
            click.echo(msg)
            return ctx.invoke(f, *args, **kwargs)

        return update_wrapper(new_func, f)


class on_started(object):
    def __init__(self, callback):
        self.callback = callback
        self.exec_before = True

    def invoke_callback(self, ctx):
        if isinstance(self.callback, basestring):
            cmd = ctx.parent.command.get_command(ctx, self.callback)
            ctx.invoke(cmd)
        else:
            self.callback(ctx.obj)

    def __call__(self, f):
        @click.pass_context
        def new_func(ctx, *args, **kwargs):
            try:
                if self.exec_before:
                    self.invoke_callback(ctx)
                return ctx.invoke(f, *args, **kwargs)
            finally:
                if not self.exec_before:
                    self.invoke_callback(ctx)
        return update_wrapper(new_func, f)


class on_finished(on_started):
    def __init__(self, callback):
        super(on_finished, self).__init__(callback)
        self.exec_before = False
