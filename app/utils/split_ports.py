def split_ports(ports: list[dict]) -> tuple[list[int], list[int]]:
    if not ports:
        return [], []

    internal = [p["internal"] for p in ports if "internal" in p]
    published = [p["published"] for p in ports if "published" in p]
    return internal, published
