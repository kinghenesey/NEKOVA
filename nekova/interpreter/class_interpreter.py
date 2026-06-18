# =============================================================
# NEKOVA — Class Interpreter Mixin  (Phase 6)
# =============================================================

from nekova.interpreter.nekova_class import NEKOVAClass, NEKOVAInstance
from nekova.parser.nodes import (
    ClassDefinition, MethodDefinition, NewInstance,
    SelfAccess, SelfAssign, PropertyAccess, MethodCall,
)

class ClassInterpreterMixin:
    """Mixed into Interpreter to handle class/object execution."""

    # ── class definition ──────────────────────────────────────

    def _exec_ClassDefinition(self, node: ClassDefinition):
        """Register a class in the environment."""
        # Resolve parent class if specified
        parent = None
        if node.parent:
            parent = self.env.get(node.parent)
            if not isinstance(parent, NEKOVAClass):
                raise RuntimeError(
                    f"'{node.parent}' is not a class — "
                    f"cannot extend it."
                )

        methods = {m.name: m for m in node.methods}
        klass = NEKOVAClass(
            name        = node.name,
            fields      = node.fields,
            init_params = node.init_params,
            init_body   = node.init_body,
            methods     = methods,
            parent      = parent,
        )
        self.env[node.name] = klass
        return klass

    # ── new instance ─────────────────────────────────────────

    def _exec_NewInstance(self, node: NewInstance):
        """Instantiate a class: new Person("Emmanuel", 25)"""
        klass = self.env.get(node.class_name)
        if klass is None:
            raise RuntimeError(
                f"Class '{node.class_name}' is not defined.\n"
                f"  Declare it with:  object {node.class_name}:"
            )
        if not isinstance(klass, NEKOVAClass):
            raise RuntimeError(
                f"'{node.class_name}' is not a class."
            )

        instance = NEKOVAInstance(klass)

        # Run init if defined
        if klass.init_params or klass.init_body:
            args = [self._execute_node(a) for a in node.args]
            self._run_init(instance, klass, args)
        elif node.args:
            args = [self._execute_node(a) for a in node.args]
            # No init defined — assign positional args to fields in order
            for i, (fname, _) in enumerate(klass.get_all_fields()):
                if i < len(args):
                    instance.set_attr(fname, args[i])

        return instance

    def _run_init(self, instance: NEKOVAInstance,
                  klass: NEKOVAClass, args: list):
        """Execute the init body with self bound to instance."""
        from nekova.interpreter.environment import Environment
        from nekova.runtime import ReturnSignal
        env_backup = self.env
        local_env = Environment(parent=self.globals)

        # Bind init params
        for i, (pname, _) in enumerate(klass.init_params):
            local_env.set(pname, args[i] if i < len(args) else None)

        # Bind self
        local_env.set("__self__", instance)
        self.env = local_env

        try:
            for stmt in klass.init_body:
                self._execute_node(stmt)
        except ReturnSignal:
            pass  # return in init is valid but ignored
        finally:
            self.env = env_backup

    # ── method call on instance ───────────────────────────────

    def _call_instance_method(self, instance: NEKOVAInstance,
                               method_name: str, args: list):
        """Execute a method on an instance."""
        method = instance._class.get_method(method_name)
        if method is None:
            raise RuntimeError(
                f"'{instance._class.name}' has no method '{method_name}'.\n"
                f"  Available methods: "
                f"{list(instance._class.methods.keys()) or '(none)'}"
            )

        from nekova.interpreter.environment import Environment
        from nekova.runtime import ReturnSignal
        local_env = Environment(parent=self.globals)

        # Bind method params
        for i, (pname, _) in enumerate(method.params):
            local_env.set(pname, args[i] if i < len(args) else None)

        # Bind self
        local_env.set("__self__", instance)

        env_backup = self.env
        self.env = local_env
        result = None
        try:
            for stmt in method.body:
                self._execute_node(stmt)
        except ReturnSignal as r:
            result = r.value
        finally:
            self.env = env_backup
        return result

    # ── self access / assignment ──────────────────────────────

    def _exec_SelfAccess(self, node: SelfAccess):
        """self.attribute — read an instance attribute."""
        instance = self._get_self()
        return instance.get_attr(node.attribute)

    def _exec_SelfAssign(self, node: SelfAssign):
        """self.attribute = value"""
        instance = self._get_self()
        value = self._execute_node(node.value)
        instance.set_attr(node.attribute, value)
        return value

    def _get_self(self) -> NEKOVAInstance:
        """Retrieve the current 'self' instance from env."""
        try:
            instance = self.env.get("__self__")
        except Exception:
            instance = None
        if not isinstance(instance, NEKOVAInstance):
            raise RuntimeError(
                "'self' can only be used inside an object method or init."
            )
        return instance

    # ── property access on instances ─────────────────────────

    def _exec_PropertyAccess_instance(self, obj, prop: str):
        """Called by _exec_PropertyAccess when obj is NEKOVAInstance."""
        if isinstance(obj, NEKOVAInstance):
            attr = obj.get_attr(prop)
            return attr
        return NotImplemented

    # ── method call on instances (via _exec_MethodCall) ───────

    def _call_method_on_instance(self, obj, method_name: str, args: list):
        """Called by _exec_MethodCall when obj is NEKOVAInstance."""
        if isinstance(obj, NEKOVAInstance):
            return self._call_instance_method(obj, method_name, args)
        return NotImplemented