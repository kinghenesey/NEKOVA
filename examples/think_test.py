#!/usr/bin/env python3
# Compiled NEKOVA Program — NEKOVA Compiler v1.0.0
import os, sys, re, time, random

_nekova_root = 'C:/Users/HomePC/Desktop/NEKOVA'
if _nekova_root not in sys.path:
    sys.path.insert(0, _nekova_root)

def _nekova_show(value):
    if value is None:    print('null')
    elif value is True:  print('true')
    elif value is False: print('false')
    else:                print(str(value))

def _nekova_think(prompt):
    try:
        from ai.providers import get_provider
        provider = get_provider()
        response = provider.ask(str(prompt))
        print('\033[96m🧠 ' + response + '\033[0m')
        return response
    except Exception as e:
        print('[think error: ' + str(e) + ']')
        return ''

def _nekova_interpolate(text, local_vars):
    import re
    def replace(m):
        name = m.group(1)
        return str(local_vars.get(name, m.group(0)))
    return re.sub(r'{(\w+)}', replace, text)

def _nekova_to_string(v):
    if v is None:  return 'null'
    if v is True:  return 'true'
    if v is False: return 'false'
    return str(v)

def type_of(x):       return type(x).__name__
def to_number(x):     return float(x) if '.' in str(x) else int(x)
def to_text(x):       return str(x)
def length(x):        return len(x)
def ask(p=''):        return input(str(p))
def clear():          print('\033[H\033[J', end='')
def sleep(s=1):       time.sleep(float(s))
def random_num(a, b): return random.randint(int(a), int(b))

_nekova_think(_nekova_interpolate('What is the capital of Nigeria?', locals()))
thought = _nekova_think(_nekova_interpolate('Give me one productivity tip in one sentence', locals()))
_nekova_show(_nekova_interpolate('AI said: {thought}', locals()))
topic = _nekova_interpolate('Python programming', locals())
result = _nekova_think(_nekova_interpolate('Give me one fun fact about {topic}', locals()))
_nekova_show(result)