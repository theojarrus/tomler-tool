import argparse
import os
import tomllib
from logging import basicConfig, info, error, INFO

TOML_KEY_VERSIONS = "versions"
TOML_KEY_LIBRARIES = "libraries"
TOML_KEY_GROUP = "group"
TOML_KEY_NAME = "name"
TOML_KEY_MODULE = "module"
TOML_KEY_VERSION = "version"
TOML_KEY_VERSION_REF = "ref"
TOML_KEY_VERSION_STRICTLY = "strictly"

TOML_DIVIDER_MODULE = ":"
TOML_DIVIDER_EQUALS = " = "

TABLE_DIVIDER_COLUMN = " | "
TABLE_DIVIDER_ROW = "-"

TABLE_HEADER_VERSION = "Version"
TABLE_HEADER_REFERENCE = "Reference"


def parse_args():
    parser = argparse.ArgumentParser(fromfile_prefix_chars='@')
    parser.add_argument("--compare", type=str, nargs="+", help="paths to files to compare", required=True)
    parser.add_argument("--downgrade", type=str, nargs="+", help="paths to files whose versions need to be downgraded")
    parser.add_argument("--ignore", type=str, nargs="+", help="modules or references ignored when downgrading")
    args = parser.parse_args()
    return args


def get_file_name(path):
    return os.path.basename(path)


def read_file(path):
    with open(path, "r") as file:
        return file.readlines()


def read_files(paths):
    return {path: read_file(path) for path in paths}


def write_file(path, lines):
    with open(path, "w") as file:
        file.writelines(lines)


def write_files(files):
    for path, lines in files.items():
        write_file(path, lines)


def read_file_toml(path):
    with open(path, "rb") as file:
        return tomllib.load(file)


def read_files_toml(paths):
    return {path: read_file_toml(path) for path in paths}


def parse_library_version(versions, library):
    version, version_reference = None, None
    if TOML_KEY_VERSION in library:
        version = library[TOML_KEY_VERSION]
        if TOML_KEY_VERSION_REF in version:
            version_reference = version[TOML_KEY_VERSION_REF]
            version = versions[version_reference]
        if TOML_KEY_VERSION_STRICTLY in version:
            version = version[TOML_KEY_VERSION_STRICTLY]
    return version, version_reference


def find_group_version(groups, module):
    for group, version in groups.items():
        if group in module:
            return version
    error(f"Error: module '{module}' has no version")
    return None, None


def parse_module(groups, library, version, version_reference):
    module = library[TOML_KEY_MODULE]
    if version is None:
        version, version_reference = find_group_version(groups, module)
    return module, version, version_reference


def parse_group(library):
    group = library[TOML_KEY_GROUP]
    name = library[TOML_KEY_NAME]
    module = group + TOML_DIVIDER_MODULE + name
    return module, group, name


def save_group(groups, group, name, version, version_reference):
    if version is not None:
        groups[group] = (version, version_reference)
    else:
        error(f"Error: group '{group}' with name '{name}' has no version")


def parse_inline_module(module):
    return module.rsplit(TOML_DIVIDER_MODULE, 1)


def parse_library(versions, groups, library):
    version, version_reference = parse_library_version(versions, library)
    if TOML_KEY_MODULE in library:
        module, version, version_reference = parse_module(groups, library, version, version_reference)
    elif TOML_KEY_GROUP in library:
        module, group, name = parse_group(library)
        save_group(groups, group, name, version, version_reference)
    else:
        module, version = parse_inline_module(library)
    return module, version, version_reference


def save_module(versions, path, module, version, version_reference):
    if module not in versions:
        versions[module] = dict()
    if version not in versions[module]:
        versions[module][version] = dict()
    versions[module][version][path] = version_reference


def parse_modules(datas):
    modules = dict()
    for path, data in datas.items():
        groups = dict()
        versions, libraries = data[TOML_KEY_VERSIONS], data[TOML_KEY_LIBRARIES]
        for library in libraries.values():
            module, version, version_reference = parse_library(versions, groups, library)
            save_module(modules, path, module, version, version_reference)
    return modules


def is_module_versions_differ(versions):
    return len(versions.values()) > 1


def is_file_line_matches_module(line, module, version_reference):
    if version_reference is not None:
        return version_reference + TOML_DIVIDER_EQUALS in line
    if TOML_KEY_GROUP in line:
        group, name = parse_inline_module(module)
        return group in line and name in line
    if TOML_KEY_MODULE in line:
        return module in line


def find_file_module_line(lines, module, version_reference):
    for index, line in enumerate(lines):
        if is_file_line_matches_module(line, module, version_reference):
            return index, line


def replace_file_module_version(datas, module, version_reference, version, required_version, path):
    index, line = find_file_module_line(datas[path], module, version_reference)
    datas[path][index] = line.replace(version, required_version)


def replace_files_version(datas, ignored, module, files, version, required_version):
    for path, version_reference in files.items():
        if path in datas.keys() and module not in ignored and version_reference not in ignored:
            replace_file_module_version(datas, module, version_reference, version, required_version, path)
            info(f"Replaced '{module}' from '{version}' ({version_reference}) to '{required_version}' in '{path}'")


def downgrade_files_module_version(datas, ignored, module, versions):
    required_version = min(versions.keys())
    for version, files in versions.items():
        if version != required_version:
            replace_files_version(datas, ignored, module, files, version, required_version)


def downgrade_files_modules(datas, ignored, modules):
    for module, versions in modules.items():
        if is_module_versions_differ(versions):
            downgrade_files_module_version(datas, ignored, module, versions)


def get_table_versions_rows(versions):
    return [
        [get_file_name(path), version, str(version_reference)]
        for version, files in versions.items() for path, version_reference in files.items()
    ]


def get_table_columns_widths(rows):
    columns = [[row[column] for row in rows] for column in range(min(map(len, rows)))]
    widths = [max(map(len, column)) for column in columns]
    return widths


def get_table_row_width(columns_widths):
    return sum(columns_widths) + len(TABLE_DIVIDER_COLUMN) * (len(columns_widths) - 1)


def get_table_row_divider(width):
    return TABLE_DIVIDER_ROW * width


def get_table_line(columns_widths):
    return TABLE_DIVIDER_COLUMN.join(f"{{:<{width}}}" for width in columns_widths)


def print_table_rows(rows, columns_widths, table_width):
    info(get_table_row_divider(table_width))
    for row in rows:
        info(get_table_line(columns_widths).format(*row))


def print_table(module, versions):
    header = [[module, TABLE_HEADER_VERSION, TABLE_HEADER_REFERENCE]]
    rows = header + get_table_versions_rows(versions)
    columns_widths = get_table_columns_widths(rows)
    table_width = get_table_row_width(columns_widths)
    print_table_rows(rows, columns_widths, table_width)


def print_modules(modules):
    for module, versions in modules.items():
        if is_module_versions_differ(versions):
            print_table(module, versions)


def main():
    # setup logging
    basicConfig(level=INFO, format='%(message)s')
    # parse command line arguments
    arguments = parse_args()
    # get command line arguments
    paths = arguments.compare
    downgradable_paths = arguments.downgrade
    downgrade_ignored = arguments.ignore or list()
    # read toml datas from files
    datas = read_files_toml(paths)
    # parse each toml data to dictionary with modules versions
    modules = parse_modules(datas)
    # downgrade modules version for each downgradable file to required - minimal
    if downgradable_paths is not None:
        # read downgradable files lines from paths
        downgradable_datas = read_files(downgradable_paths)
        # replace modules versions in downgradable files lines
        downgrade_files_modules(downgradable_datas, downgrade_ignored, modules)
        # write changed lines for each file
        write_files(downgradable_datas)
    # print tables with different versions modules
    print_modules(modules)


if __name__ == '__main__':
    main()
