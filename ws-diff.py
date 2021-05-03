import sys
import json
from csv_diff import load_csv, compare

def diff(file1, file2, k):
    delta = compare(
        load_csv(open(file1), key=k),
        load_csv(open(file2), key=k),
        True
    )
    return delta


def header(title,c='-'): 
    print()
    print(c * (len(title) + 1))
    print(title)
    print(c * (len(title) + 1))


def pw(wine):
    print(wine["Name"].replace(',',''), wine["Type"], wine["Px"], wine["Px Unit"], wine["Bulk Px"], wine["Bulk Unit"], sep=", ")


def specials(wines):

    header("SPECIALS")
    units = ['magnum','imperial','jeroboam']
    names = ['trevallon','mendel','batailley','gruaud','larose','vivens','wassmer',
                'zapata','cakebread','soula','trévallon',
                'beaucastel','poyferre','guadet','pontet','lacoste','troplong','mondot','loosen','talbot',  
                'muga','contino',
                'sondraia','canneto','contucci','sassicaia','guido','ornellaia','brunelli','fontodi','isole','vajra',
                'madeira','ximenez','osborne',
                'jeroboam','magnum','imperial'
                ]
    
    for w in wines:
        if any(n in w["Name"].lower() for n in names) or any(u in w["Px"].lower() for u in units):
            pw(w)


def changes(wines):
    header("PRICE CHANGES")
    mask = "{x} => {y} per {z}"
    
    for w in wines:
        c = w["changes"]
        u = w['unchanged']
        name = u["Name"] if "Name" in u else c["Name"][1]
        pxUnit = u["Px Unit"] if "Px Unit" in u else c["Px Unit"][1]
        bulkUnit = u["Bulk Unit"] if "Bulk Unit" in u else c["Bulk Unit"][1]

        px = None
        if "Px" in c:
            px = mask.format(x=c["Px"][0], y=c["Px"][1], z=pxUnit)

        bpx = None
        if "Bulk Px" in c:
            bpx = mask.format(x=c["Bulk Px"][0], y=c["Bulk Px"][1], z=bulkUnit)

        if px is not None or bpx is not None:
            print(name, px or '', bpx or '', sep=', ')    


def pall(wines, title):
    header(title)
    for w in wines:
        pw(w)


def main():
    
    f1 = sys.argv[1] if len(sys.argv) >= 3 else '20210412.txt'
    f2 = sys.argv[2] if len(sys.argv) >= 3 else '20210424.txt'
    
    fullscan = False
    
    f1 = 'empty.csv' if fullscan else f1

    delta = diff(f1, f2, 'Code')

    specials(delta["added"])
    changes(delta["changed"])
    
    pall(delta["added"],"NEW IN")
    pall(delta["removed"],"OUT OF STOCK")

    #with open('delta.json', 'w') as f:
    #    print(json.dumps(delta, indent = 4, sort_keys=True), file=f )


if __name__ == '__main__':
    main()
    