---
title: Optional Chaining
lede: "The ?. operator short-circuits to null instead of raising when the thing you're accessing is null."
---

## Basic usage

```nekova
let user = null
show user?.email   # null — no error
```

```nekova
let user = {"name": "Sam", "email": "s@example.com"}
show user?.email   # "s@example.com" — behaves like a normal access when not null
```

## Method calls

```nekova
let name = null
show name?.upper()   # null

let name2 = "sam"
show name2?.upper()  # "SAM"
```

## Chaining through multiple links

```nekova
let user = null
show user?.profile?.email   # null — short-circuits at the first null link
```

## Only the explicit ?. short-circuits

A plain `.` after a null result still raises — only the `?.` you actually write protects that specific link:

```nekova
let user = null
show user?.profile.email
```

This raises, because `user?.profile` evaluates to `null`, and `.email` (a plain dot, not `?.`) on `null` is not protected. If you want the whole chain to be safe, use `?.` at every link that might be null.

## What ?. does not do

`?.` only checks whether the object itself is `null`. It doesn't suppress other kinds of errors — accessing a genuinely missing key on a dict that *isn't* null still raises normally, listing the keys that were actually available.