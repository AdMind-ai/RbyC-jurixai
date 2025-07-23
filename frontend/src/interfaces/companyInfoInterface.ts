export interface CompanyInfoAdm {
    long_name: string;
    short_name: string;
    stock_symbol: string;
    website: string;
    description: string;
    sector: string;
    country: string;
    state: string;
    city: string;
    address: string;
    phone: string;
    email: string;
    competitors: {
      name: string;
      stock_symbol: string;
      sector: string;
      website: string;
    }[];
    ceos: {
      name: string;
      role: string;
    }[];
}