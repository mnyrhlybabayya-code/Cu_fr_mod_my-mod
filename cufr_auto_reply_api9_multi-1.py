# ba_meta require api 9
# ba_meta export babase.Plugin
"""BSLife CU/FR auto-reply helper for up to six configured names.

Based on the earlier BSLife chat-only implementation. It learns each name's
number only when chat explicitly shows a name/number association; it does not
guess player numbers or use ClassicAppMode roster APIs.
"""
import re
import babase
import bascenev1 as bs

# Enter up to six exact in-game names here, separated by commas.
SELF_NAMES = ('eon', 'Lunox', 'Ava')
POLL_SECONDS = 0.15

class Mod(babase.Plugin):
    def __init__(self):
        self._last_messages = []
        self._self_numbers = {}  # casefolded name -> learned player number
        self._seen_requests = set()
        self._timer = bs.AppTimer(POLL_SECONDS, self._poll, repeat=True)

    def _poll(self):
        try:
            messages = list(bs.get_chat_messages() or [])
        except Exception:
            return

        # Only process newly appended messages.
        overlap = 0
        max_overlap = min(len(self._last_messages), len(messages))
        for n in range(max_overlap, 0, -1):
            if self._last_messages[-n:] == messages[:n]:
                overlap = n
                break
        new_messages = messages[overlap:]
        self._last_messages = messages

        names = []
        for raw_name in SELF_NAMES:
            name = str(raw_name).strip()
            if name and name.casefold() not in [n.casefold() for n in names]:
                names.append(name)
            if len(names) >= 6:
                break

        for raw in new_messages:
            msg = str(raw)

            # Learn a number only from an explicit name/number association,
            # such as "eon (168)" or "168 ... eon" in chat.
            for name in names:
                escaped = re.escape(name)
                pattern = (
                    r'(?i)\b' + escaped + r'\b[^0-9]{0,16}(\d{1,5})'
                    + r'|\b(\d{1,5})\b[^a-z]{0,16}\b' + escaped + r'\b'
                )
                match = re.search(pattern, msg)
                if match:
                    candidate = match.group(1) or match.group(2)
                    if candidate:
                        self._self_numbers[name.casefold()] = candidate

            # Respond only when the CU/FR target number belongs to one of the
            # configured names and that name's number was learned from chat.
            match = re.search(r'(?i)(?:%\s*)?(cu|fr)\s+(\d{1,5})\b', msg)
            if not match:
                continue
            kind, target = match.group(1).lower(), match.group(2)
            if target not in set(self._self_numbers.values()):
                continue

            key = (msg, kind, target)
            if key in self._seen_requests:
                continue
            self._seen_requests.add(key)
            if len(self._seen_requests) > 100:
                self._seen_requests.clear()
            try:
                bs.chatmessage('h' if kind == 'cu' else 'u')
            except Exception:
                pass
