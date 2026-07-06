---
title: CLI Commands
lede: Every command the nekova tool supports, grouped the way the CLI's own --help groups them.
---

## Running files

```bash
nekova hello.nk               # run a file
nekova hello.nk --debug       # run with debug output
nekova hello.nk --compile     # run using the compiler
nekova run hello.nk           # equivalent to the bare form above
nekova repl                   # start the interactive shell
```

## Developer tools

```bash
nekova test                   # run every test block in the project
nekova build hello.nk         # validate a file without running it
nekova new my-project         # scaffold a new project
nekova info                   # show system info
nekova clean                  # remove cache files
nekova debug hello.nk         # visual debugger
nekova ide                    # launch the web IDE
nekova format hello.nk        # format code style
nekova format --check hello.nk  # check formatting without writing
nekova check hello.nk         # run the static checker (unused variables, near-miss suggestions, etc.)
```

## Deployment

```bash
nekova compile hello.nk       # compile to native/Python
nekova export hello.nk        # export to HTML/script
nekova package my-project/    # package a project
nekova publish my-pkg.nkpkg   # publish to the registry
nekova deploy hello.nk        # full deploy pipeline
```

## Marketplace

```bash
nekova marketplace                  # browse all packages
nekova marketplace search <query>   # search packages
nekova marketplace install <name>   # install a package
nekova marketplace info <name>      # package details
nekova marketplace featured         # top packages
```

## Package manager

```bash
nekova --packages              # list installed packages
nekova --install <package>     # install a package
nekova --uninstall <package>   # uninstall a package
```

## Other

```bash
nekova --version
nekova --help
```