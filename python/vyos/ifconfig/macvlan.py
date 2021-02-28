# Copyright 2019-2020 VyOS maintainers and contributors <maintainers@vyos.io>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library.  If not, see <http://www.gnu.org/licenses/>.

from vyos.ifconfig.interface import Interface

@Interface.register
class MACVLANIf(Interface):
    """
    Abstraction of a Linux MACvlan interface
    """

    default = {
        'type': 'macvlan',
        'address': '',
        'source_interface': '',
        'mode': '',
    }
    definition = {
        **Interface.definition,
        **{
            'section': 'pseudo-ethernet',
            'prefixes': ['peth', ],
        },
    }
    options = Interface.options + \
        ['source_interface', 'mode']

    def _create(self):
        # please do not change the order when assembling the command
        cmd = 'ip link add {ifname}'
        if self.config['source_interface']:
            cmd += ' link {source_interface}'
        cmd += ' type macvlan'
        if self.config['mode']:
            cmd += ' mode {mode}'
        self._cmd(cmd.format(**self.config))

    def set_mode(self, mode):
        ifname = self.config['ifname']
        cmd = f'ip link set dev {ifname} type macvlan mode {mode}'
        return self._cmd(cmd)
