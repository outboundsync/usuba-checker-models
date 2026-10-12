### By task
| | train | holdout | total |
|---|---|---|---|
| chunk_component | 80 | 10 | 90 |
| build_from_spec | 56 | 27 | 83 |
| chunk_manifest_entry | 28 | 5 | 33 |
| fix_manifest | 19 | 5 | 24 |
| add_panel | 10 | 6 | 16 |
| chunk_add_kind | 4 | 3 | 7 |
| chunk_entry_file | 1 | 0 | 1 |

### By task (detailed)
| | train | holdout | total |
|---|---|---|---|
| chunk_component | 80 | 10 | 90 |
| build_from_spec | 56 | 27 | 83 |
| chunk_manifest_entry | 28 | 5 | 33 |
| add_panel | 10 | 6 | 16 |
| chunk_add_kind:menu | 2 | 1 | 3 |
| fix_manifest:bad_path_absolute | 2 | 1 | 3 |
| fix_manifest:missing_entry | 3 | 0 | 3 |
| fix_manifest:schema_string | 3 | 0 | 3 |
| fix_manifest:missing_entry_file | 3 | 0 | 3 |
| fix_manifest:bad_default_section | 3 | 0 | 3 |
| fix_manifest:symlink | 3 | 0 | 3 |
| fix_manifest:bad_path_dotdot | 2 | 1 | 3 |
| fix_manifest:reserved_id | 0 | 3 | 3 |
| chunk_add_kind:bar | 1 | 1 | 2 |
| chunk_add_kind:service | 1 | 1 | 2 |
| chunk_entry_file | 1 | 0 | 1 |

### By kind (an example counts once per kind it declares)
| | train | holdout | total |
|---|---|---|---|
| bar-widget | 98 | 22 | 120 |
| bar | 52 | 18 | 70 |
| service | 30 | 15 | 45 |
| menu | 29 | 10 | 39 |
| panel | 12 | 3 | 15 |
| overlay | 11 | 3 | 14 |

### By primary kind (rarest kind; holdout strata)
| | train | holdout | total |
|---|---|---|---|
| bar-widget | 82 | 22 | 104 |
| bar | 41 | 11 | 52 |
| menu | 29 | 10 | 39 |
| service | 23 | 7 | 30 |
| panel | 12 | 3 | 15 |
| overlay | 11 | 3 | 14 |

### By origin
| | train | holdout | total |
|---|---|---|---|
| community | 82 | 31 | 113 |
| first-party | 65 | 21 | 86 |
| house | 51 | 4 | 55 |

### House plugins
| | train | holdout | total |
|---|---|---|---|
| (not house) | 147 | 52 | 199 |
| omarchy-rocketlauncher | 15 | 0 | 15 |
| omarchy-sparklekeys | 13 | 0 | 13 |
| omarchy-enricherino | 9 | 0 | 9 |
| omarchy-compliantish | 8 | 0 | 8 |
| omarchy-encyclopedic | 6 | 0 | 6 |
| omarchy-scriptural | 0 | 4 | 4 |

### Origin × kind
| | train | holdout | total |
|---|---|---|---|
| community/bar | 47 | 18 | 65 |
| house/bar-widget | 51 | 4 | 55 |
| first-party/bar-widget | 29 | 13 | 42 |
| community/menu | 27 | 10 | 37 |
| community/service | 13 | 11 | 24 |
| community/bar-widget | 18 | 5 | 23 |
| first-party/service | 17 | 4 | 21 |
| first-party/panel | 9 | 2 | 11 |
| first-party/overlay | 8 | 2 | 10 |
| first-party/bar | 5 | 0 | 5 |
| community/overlay | 3 | 1 | 4 |
| community/panel | 3 | 1 | 4 |
| first-party/menu | 2 | 0 | 2 |

### Full plugin vs chunked
| | train | holdout | total |
|---|---|---|---|
| chunked | 113 | 18 | 131 |
| full/fix | 85 | 38 | 123 |

### By complexity
| | train | holdout | total |
|---|---|---|---|
| large | 159 | 38 | 197 |
| small | 31 | 8 | 39 |
| medium | 8 | 10 | 18 |
