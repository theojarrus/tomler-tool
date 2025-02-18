# Tomler

Tomler. Easy tool for comparing and synchronizing versions in toml files

## Problem

If you have ever connected a library from one project to another, you have encountered the problem of conflicting versions of other dependences. Tomler is designed to simplify the process of comparing and synchronizing versions for systems using toml.

## Requirements

You must use Python version `3.11` due to the `tomllib` module

## Usage

#### Compare versions

```shell
python3 tomler.py --compare first.toml second.toml third.toml
```

#### Compare versions, downgrade `first.toml` to minimal versions, but ignore `composeBom` and `kotlinx-serialization` dependencies

```shell
python3 tomler.py \
  --compare first.toml second.toml \
  --downgrade first.toml \
  --ignore composeBom org.jetbrains.kotlinx:kotlinx-serialization-json
```

#### Paste arguments from file

```shell
python3 tomler.py @arguments
```

Where file named `arguments` contains:

```shell
--compare
first.versions.toml
second.versions.toml
--downgrade
first.versions.toml
--ignore
composeBom
org.jetbrains.kotlinx:kotlinx-serialization-json
```

### Arguments

| Key | Value     | Description                       |
| :-------- | :-------  |  :-------------------------------- |
| `--compare`      | **required** | List of paths to compared toml files |
| `--downgrade`      | *optional* | List of paths to toml files that need to be downgraded to minimum versions |
| `--ignore`      | *optional* | List of dependencies to ignore for `--downgrade` |

#### Important
- When specifying a dependency in `--ignore`, the name must be written in full. For example, to ignore a dependency like `moba-buildMetrics = { group = "com.example.moba", name = "build-metrics" }`, the correct query would be `--ignore com.example.moba:build-metrics`.
- If a dependency has version reference, the `--ignore` must specify the reference, otherwise the reference version may be downgraded due to another dependency using the same reference.

## How it works

#### Comparsion

It goes through all the dependencies from the toml file, brings them to a common format (since there are many ways to write a dependency, for example, inline, via module or via group, similarly there is variability with the version indication). Then puts it into a dictionary of the following type:

```json
{
    "example.library": {
        "3.2.2": {
            "file1": "exampleVersionReference",
            "file2": None
        },
        "4.5.2": {
            "file3": "exampleVersionOtherReference",
        }
    }
}
```

Next, simply print this dictionary in the required format.

#### Downgrade

It goes through the modules from the previously parsed dictionary, selects modules that have more than one version, which means that they differ in some files, and takes the minimum version. Then it goes through all the files where the version differs from the minimum, if they are in the list from the `--downgrade` argument, then it finds a reference or module in the lines and replaces the version.

## Contribution

At the moment, Tomler is considered ready and does not need any improvements. But if you have any ideas on how to improve it, feel free to contribute.
