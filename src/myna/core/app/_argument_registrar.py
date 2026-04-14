#
# Copyright (c) Oak Ridge National Laboratory.
#
# This file is part of Myna. For details, see the top-level license
# at https://github.com/ORNL-MDF/Myna/LICENSE.md.
#
# License: 3-clause BSD, see https://opensource.org/licenses/BSD-3-Clause.
#
"""Private helper for idempotent argparse registration in `MynaApp`."""


class _ArgumentRegistrar:
    """Register argparse options while rejecting conflicting re-definitions."""

    def __init__(self, parser):
        self.parser = parser
        self._argument_registry = {}

    def _infer_dest(self, option_strings, positional_name, kwargs):
        """Infer the argparse destination in the same style as argparse."""

        if "dest" in kwargs:
            return kwargs["dest"]
        if option_strings:
            long_options = [
                option for option in option_strings if option.startswith("--")
            ]
            preferred = long_options[0] if long_options else option_strings[0]
            return preferred.lstrip("-").replace("-", "_")
        return positional_name

    def _normalize_argument_signature(self, *name_or_flags, **kwargs):
        """Return the registration fields used to compare duplicates."""

        option_strings = tuple(
            sorted(
                option
                for option in name_or_flags
                if isinstance(option, str) and option.startswith("-")
            )
        )
        positional_names = [
            name
            for name in name_or_flags
            if isinstance(name, str) and not name.startswith("-")
        ]
        positional_name = positional_names[0] if positional_names else None
        return {
            "option_strings": option_strings,
            "dest": self._infer_dest(option_strings, positional_name, kwargs),
            "action": kwargs.get("action", "store"),
            "nargs": kwargs.get("nargs"),
            "const": kwargs.get("const"),
            "default": kwargs.get("default"),
            "type": kwargs.get("type"),
            "choices": tuple(kwargs.get("choices")) if kwargs.get("choices") else None,
            "required": kwargs.get("required", False),
            "metavar": kwargs.get("metavar"),
        }

    def _get_argument_identities(self, signature):
        """Return registry keys for an argument registration.

        Optional arguments are keyed by option string so shared aliases map back to
        one action. Positional arguments do not have option strings, so `dest` is the
        stable identity used to detect collisions.
        """

        if signature["option_strings"]:
            return [("option", option) for option in signature["option_strings"]]
        return [("dest", signature["dest"])]

    def _raise_argument_registration_error(
        self,
        identity,
        existing_entry,
        new_signature,
    ):
        """Raise a descriptive error for an invalid duplicate registration."""

        identity_type, identity_value = identity
        identity_label = (
            f"option '{identity_value}'"
            if identity_type == "option"
            else f"dest '{identity_value}'"
        )
        raise ValueError(
            "Conflicting argument registration for "
            f"{identity_label}. "
            f"Existing signature: {existing_entry['signature']}; "
            f"new signature: {new_signature}."
        )

    def register(self, *name_or_flags, **kwargs):
        """Register an argument while allowing exact duplicate re-registration."""

        signature = self._normalize_argument_signature(*name_or_flags, **kwargs)
        identities = self._get_argument_identities(signature)
        existing_entries = [
            (identity, self._argument_registry[identity])
            for identity in identities
            if identity in self._argument_registry
        ]

        if existing_entries:
            reference_identity, reference_entry = existing_entries[0]
            for identity, entry in existing_entries[1:]:
                if entry is not reference_entry:
                    self._raise_argument_registration_error(
                        identity,
                        entry,
                        signature,
                    )
            if reference_entry["signature"] == signature:
                return reference_entry["action"]
            self._raise_argument_registration_error(
                reference_identity,
                reference_entry,
                signature,
            )

        action = self.parser.add_argument(*name_or_flags, **kwargs)
        entry = {"action": action, "signature": signature}
        for identity in identities:
            self._argument_registry[identity] = entry
        return action
