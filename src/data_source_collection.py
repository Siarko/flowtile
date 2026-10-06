from src.data_source import DataSource

_sources: dict[str, DataSource] = {}
_none_source = DataSource("NONE")

def register(data_source: DataSource) -> None:
    _sources[data_source.get_name()] = data_source

def get(name: str | None) -> DataSource:
    if name is not None and name in _sources:
        return _sources[name]
    return _none_source
