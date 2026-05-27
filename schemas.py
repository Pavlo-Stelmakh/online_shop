from pydantic import BaseModel


class CategoryCreate(BaseModel):
    name: str


class CategoryResponse(BaseModel):
    id: int
    name: str

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str
    price: float
    description: str
    category_id: int


class ProductResponse(BaseModel):
    id: int
    name: str
    price: float
    description: str
    category_id: int
    category: CategoryResponse

    class Config:
        from_attributes = True


class ProductCatalogResponse(BaseModel):
    items: list[ProductResponse]
    total: int
    page: int
    limit: int
    pages: int