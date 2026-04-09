"""
Multiple commands as an IR command.

Copyright 2026 Jason Rumney

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import logging

from infrared_protocols.commands import Command, Timing


class MultiCommand(Command):
    """A command that sends multiple commands in sequence."""

    def __init__(self, commands: list[Command], delayus: int = 96000):
        """
        Initialise the multi command.
        Args:
            commands (list[Command]): The list of commands to send in sequence
            delay (int): The delay between commands in milliseconds
        """
        self._commands = commands
        self._delay = delayus

    def get_raw_timings(self) -> list[Timing]:
        """Get the raw timings for the command."""
        timings = []
        for cmd in self._commands:
            if timings:
                last = timings[-1]
                timings[-1] = Timing(high_us=last.high_us, low_us=self._delay)
            timings.extend(cmd.get_raw_timings())
        return timings
