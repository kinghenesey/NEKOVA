---
title: Inheritance
lede: extends gives a class a parent's methods — but init isn't inherited automatically.
---

## Basic inheritance

```nekova
object Animal:
    init(name):
        self.name = name
    func speak():
        return self.name + " makes a sound"

object Dog extends Animal:
    init(name):
        self.name = name
    func fetch():
        return self.name + " fetches the ball"

let d = new Dog("Rex")
show d.speak()   # inherited from Animal
show d.fetch()   # defined on Dog
```

## init is not automatically inherited

A subclass needs its own `init`, even if it's identical to the parent's — NEKOVA doesn't implicitly call the parent constructor for you:

```nekova
object Animal:
    name: text
    init(name: text):
        self.name = name
    func describe():
        return f"I am {self.name}"

object Dog extends Animal:
    init(name: text):
        self.name = name

let d = new Dog("Rex")
show d.describe()   # "I am Rex" — describe() is inherited, init is repeated
```

## Overriding a method

```nekova
object Animal:
    init(name):
        self.name = name
    func speak():
        return self.name + " makes a sound"

object Cat extends Animal:
    init(name):
        self.name = name
    func speak():
        return self.name + " meows"

let c = new Cat("Whiskers")
show c.speak()   # "Whiskers meows" — Cat's own speak() wins
```