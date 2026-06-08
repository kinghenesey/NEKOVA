#!/usr/bin/env python3
# Compiled NEKOVA Program — NEKOVA Compiler v1.0.0
import os, sys, re, time, random

_aion_root = 'C:/Users/HomePC/Desktop/NEKOVA'
if _aion_root not in sys.path:
    sys.path.insert(0, _aion_root)

def _aion_show(value):
    if value is None:    print('null')
    elif value is True:  print('true')
    elif value is False: print('false')
    else:                print(str(value))

def _aion_think(prompt):
    try:
        from ai.providers import get_provider
        provider = get_provider()
        response = provider.ask(str(prompt))
        print('\033[96m🧠 ' + response + '\033[0m')
        return response
    except Exception as e:
        print('[think error: ' + str(e) + ']')
        return ''

def _aion_interpolate(text, local_vars):
    import re
    def replace(m):
        name = m.group(1)
        return str(local_vars.get(name, m.group(0)))
    return re.sub(r'{(\w+)}', replace, text)

def _aion_to_string(v):
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

_aion_think(_aion_interpolate('What is the capital of Nigeria?', locals()))
thought = _aion_think(_aion_interpolate('Give me one productivity tip in one sentence', locals()))
_aion_show(_aion_interpolate('AI said: {thought}', locals()))
topic = _aion_interpolate('Python programming', locals())
result = _aion_think(_aion_interpolate('Give me one fun fact about {topic}', locals()))
_aion_show(result)