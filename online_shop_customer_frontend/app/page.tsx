import Image from "next/image";

export const dynamic = "force-dynamic";

type Product = {
  id: number;
  name: string;
  description: string;
  price: number;
  price_amount?: string;
  image_url?: string | null;
  stock: number;
};

type ProductsResponse = {
  items: Product[];
};

const apiBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function getProducts(): Promise<Product[]> {
  const response = await fetch(`${apiBaseUrl}/products`, { cache: "no-store" });

  if (!response.ok) {
    throw new Error("Не вдалося завантажити каталог товарів");
  }

  const data = (await response.json()) as ProductsResponse;

  return data.items;
}

function formatPrice(product: Product) {
  return product.price_amount ?? product.price.toFixed(2);
}

export default async function Home() {
  const products = await getProducts();

  return (
    <section className="space-y-8">
      <div className="space-y-3">
        <p className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Клієнтська панель online shop
        </p>
        <h1 className="text-4xl font-bold tracking-tight text-slate-950 sm:text-5xl">Каталог</h1>
      </div>

      {products.length > 0 ? (
        <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {products.map((product) => (
            <article
              key={product.id}
              className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm"
            >
              <div className="relative flex h-56 items-center justify-center bg-slate-100 text-slate-500">
                {product.image_url ? (
                  <Image
                    src={product.image_url}
                    alt={product.name}
                    fill
                    sizes="(min-width: 1024px) 33vw, (min-width: 640px) 50vw, 100vw"
                    className="object-cover"
                  />
                ) : (
                  <span className="text-sm font-medium">Немає фото</span>
                )}
              </div>

              <div className="space-y-3 p-5">
                <h2 className="text-xl font-semibold text-slate-950">{product.name}</h2>
                <p className="text-sm leading-6 text-slate-600">{product.description}</p>
                <p className="text-lg font-bold text-slate-950">{formatPrice(product)} грн</p>
                <p className="text-sm font-medium text-slate-700">В наявності: {product.stock}</p>
              </div>
            </article>
          ))}
        </div>
      ) : (
        <div className="rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm sm:p-12">
          <p className="text-lg text-slate-700">Каталог товарів порожній.</p>
        </div>
      )}
    </section>
  );
}
