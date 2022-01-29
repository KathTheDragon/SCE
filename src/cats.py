from dataclasses import dataclass

@dataclass
class Category:
    elements: list[str]
    name: str | None = None

    def __str__(self) -> str:
        if self.name is not None:
            return self.name
        else:
            return ', '.join(self.elements)

    def __getitem__(self, item: int) -> str:
        return self.elements[item]

    def __contains__(self, item: str) -> bool:
        return item in self.elements

    def index(self, item: str) -> int:
        for i, element in enumerate(self.elements):
            if element == item:
                return i
        raise ValueError(f'{item!r} is not in category')
