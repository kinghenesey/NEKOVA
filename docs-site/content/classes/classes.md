---
title: Classes
lede: object defines a class — fields, an init, and methods, all with the vocabulary NEKOVA uses instead of Python's.
---

## Defining a class

```nekova
object Person:
    name: text
    age: number

    init(name, age):
        self.name = name
        self.age = age

    func greet():
        return f"Hi, I am {self.name}"

let p = new Person("Ada", 30)
show p.greet()
show p.name
show p.age
```

NEKOVA uses `object` where many languages use `class`, and `new` to instantiate.

## Fields

Field declarations (`name: text`, `age: number`) are documentation of shape — the actual values are set in `init` via `self.name = name`.

## Docstrings

Classes, `init`, and methods can all carry a leading string as documentation:

```nekova
object Person:
    """Represents a person."""

    init(name):
        """Creates a new person."""
        self.name = name

    func greet():
        """Returns a greeting."""
        return f"Hi, I am {self.name}"

show doc(Person)             # "Represents a person."
show doc(Person, "init")     # "Creates a new person."
show doc(Person, "greet")    # "Returns a greeting."
```

## Methods calling other methods

```nekova
object Circle:
    init(radius):
        self.radius = radius

    func area():
        return 3.14159 * self.radius * self.radius

    func describe():
        return f"A circle with area {self.area()}"

let c = new Circle(5)
show c.describe()
```