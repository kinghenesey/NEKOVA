---
title: Pipe Operator
lede: "The |> operator chains transformations left to right, without nested calls or throwaway intermediate variables."
---

## Basic usage

```nekova
task double(x):
    return x * 2

task add_one(x):
    return x + 1

let result = 5 |> double |> add_one
show result   # 11
```

Without the pipe operator, the same computation reads inside-out:

```nekova
let result = add_one(double(5))
```

`|>` reads in the order the operations actually happen, which matters more the longer the chain gets.

## Chaining more steps

```nekova
task clean(text):
    return text.trim()

task shout(text):
    return text.upper()

let result = "  hello world  " |> clean |> shout
show result   # "HELLO WORLD"
```

## Where it pairs naturally

`|>` is particularly suited to `think`-based pipelines, where each stage transforms a document or a response into the next stage's input — see [think](../ai-native/think.html).