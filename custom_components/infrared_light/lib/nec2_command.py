"""
NEC Protocol without repeat codes

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

from infrared_protocols.commands import NECCommand, Timing


class NEC2Command(NECCommand):
    """A command that sends multiple commands in sequence."""

    repetition_count: int

    def __init__(
        self, *, address: int, command: int, modulation: int, repeat_count: int = 0
    ) -> None:
        """
        Initialise an NEC2Command
        """
        self.repeatition_count = repeat_count
        super().__init__(
            address=address,
            command=command,
            modulation=modulation,
            repeat_count=0,
        )

    def get_raw_timings(self) -> list[Timing]:
        """Get the raw timings for the command."""

        frame_gap = 96000  # Gap to make total frame ~108ms
        timings = super().get_raw_timings()

        for _ in range(self.repeatition_count):
            last_timing = timings[-1]
            timings[-1] = Timing(high_us=last_timing.high_us, low_us=frame_gap)
            timings.extend(super().get_raw_timings())
        return timings
