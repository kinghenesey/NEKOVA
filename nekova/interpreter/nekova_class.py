# NEKOVA — Class & Instance runtime representations
# Provides NEKOVAClass and NEKOVAInstance used by the class interpreter mixin.

from typing import List, Tuple, Dict, Optional


class NEKOVAClass:
    """Runtime representation of a NEKOVA class/object."""
    def __init__(self, name: str,
                 fields: List[Tuple[str, str]],
                 init_params: List[Tuple[str, str]],
                 init_body: List,
                 methods: Dict[str, object],
                 parent: Optional['NEKOVAClass'] = None):
        self.name = name
        self.fields = fields or []
        self.init_params = init_params or []
        self.init_body = init_body or []
        self.methods = methods or {}
        self.parent = parent

    def get_method(self, name: str):
        """Return MethodDefinition for name, searching parents."""
        if name in self.methods:
            return self.methods[name]
        if self.parent:
            return self.parent.get_method(name)
        return None

    def get_all_fields(self):
        """Return combined list of (name, hint) from parents first."""
        if self.parent:
            return self.parent.get_all_fields() + list(self.fields)
        return list(self.fields)

    def __repr__(self):
        return f"NEKOVAClass({self.name})"


class NEKOVAInstance:
    """Runtime instance of a NEKOVAClass."""
    def __init__(self, klass: NEKOVAClass):
        self._class = klass
        # Initialize attributes from class fields (defaults to None)
        self._attrs = {name: None for name, _ in klass.get_all_fields()}

    def set_attr(self, name: str, value):
        # Allow creating dynamic attributes not declared as fields
        self._attrs[name] = value

    def get_attr(self, name: str):
        # Return attribute if exists, otherwise look up methods (callable descriptors)
        if name in self._attrs:
            return self._attrs[name]
        # If attribute isn't a stored field, check if it's a method name
        method = self._class.get_method(name)
        if method is not None:
            return method
        raise AttributeError(f"'{self._class.name}' has no attribute or method '{name}'")

    def __repr__(self):
        return f"NEKOVAInstance({self._class.name})"
