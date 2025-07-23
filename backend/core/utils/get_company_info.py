from core.models.company_info import CompanyInfo


def get_company_info():
    return CompanyInfo.objects.first()


def get_ceos():
    company = get_company_info()
    if not company:
        return []
    return company.ceos.all()


def get_competitors():
    company = get_company_info()
    if not company:
        return []
    return company.competitors_of.all()
