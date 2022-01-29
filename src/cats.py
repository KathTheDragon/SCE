from dataclasses import dataclass
from .utils import contains, split

@dataclass
class Category:
    elements: list[str]
    name: str | None = None

    @staticmethod
    def parse(string: str, categories: 'dict[str, Category]') -> 'Category':
        if contains(string, '|', '+'):
            elements = []
            for item in split(string, '|', '+'):
                elements.extend(Category.parse(item, categories).elements)
            return Category(elements)
        elif contains(string, '-'):
            items = split(string, '-')
            elements = Category.parse(items.pop(0), categories).elements
            for item in items:
                elements = [element for element in elements if element not in Category.parse(item, categories)]
            return Category(elements)
        elif contains(string, '&'):
            items = split(string, '&')
            elements = Category.parse(items.pop(0), categories).elements
            for item in items:
                elements = [element for element in elements if element in Category.parse(item, categories)]
            return Category(elements)
        elif contains(string, ','):
            return Category(list(filter(None, split(string, ','))))
        else:
            return categories[string]

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
