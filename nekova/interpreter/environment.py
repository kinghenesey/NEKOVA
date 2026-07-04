# =============================================================
# NEKOVA Interpreter — Environment (Variable Storage)
# =============================================================
# The Environment is NEKOVA's memory system.
# It stores variables and handles scope.
#
# Scope means:
#   - Variables created inside a task stay inside that task
#   - Variables created at the top level are global
#
# How it works:
#   - Each Environment has its own dictionary of variables
#   - Each Environment can have a "parent" Environment
#   - When looking up a variable we check current scope first
#   - If not found we check the parent scope
#   - This creates a chain: local → global
#
# Example:
#   global scope:  name = "Emmanuel"
#   task scope:    age  = 20
#   looking up "name" inside task → found in global scope


class Environment:
    """
    Stores variables for a single scope level.

    Usage:
        # Global scope
        env = Environment()
        env.set("name", "Emmanuel")
        env.get("name")  # → "Emmanuel"

        # Local scope (inside a task)
        local = Environment(parent=env)
        local.set("age", 20)
        local.get("age")   # → 20      (found in local)
        local.get("name")  # → "Emmanuel" (found in parent)
    """

    def __init__(self, parent=None):
        self.variables = {}
        self.consts    = set()   # names declared with 'const' in THIS scope
        self.parent    = parent

    def get(self, name: str):
        """
        Look up a variable by name.
        Searches current scope first, then parent scopes.
        Raises an error if not found anywhere.
        """
        if name in self.variables:
            return self.variables[name]

        if self.parent is not None:
            return self.parent.get(name)

        raise NameError(
            f"\n  Variable '{name}' does not exist.\n"
            f"  Did you forget to define it before using it?"
        )

    def set(self, name: str, value):
        """
        Create or update a variable in the CURRENT scope.
        Always sets in current scope — never modifies parent.
        """
        self.variables[name] = value

    def update(self, name: str, value):
        """
        Update an existing variable — searches up the scope
        chain and updates it wherever it was defined.
        If not found anywhere, creates it in current scope.
        """
        if name in self.variables:
            self.variables[name] = value
            return

        if self.parent is not None:
            self.parent.update(name, value)
            return

        # Not found anywhere — create in current scope
        self.variables[name] = value

    def __repr__(self):
        return f"Environment({list(self.variables.keys())})"

    def snapshot(self):
        """Flat dict of all visible variables — used for async closure capture."""
        flat = {}
        if self.parent is not None:
            flat.update(self.parent.snapshot())
        flat.update(self.variables)
        return flat

    def keys(self):
        return self.variables.keys()

    def items(self):
        return self.variables.items()

    def __iter__(self):
        return iter(self.variables)

    def __getitem__(self, name):
        return self.get(name)

    def __setitem__(self, name, value):
        self.set(name, value)

    def __contains__(self, name):
        try:
            self.get(name)
            return True
        except NameError:
            return False