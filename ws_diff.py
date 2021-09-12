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
    names = ['trevallon','mendel','batailley','gruaud','larose','vivens','wassmer',
                'zapata','cakebread','soula','trévallon',
                'beaucastel','poyferre','guadet','pontet','lacoste','troplong','mondot','loosen','talbot',  
                'muga','contino','bohórquez','904',
                'sondraia','canneto','contucci','sassicaia','guido','ornellaia','brunelli','fontodi','isole','vajra',
                'madeira','ximenez','osborne'
                ]
    
    for w in wines:
        if any(n in w["Name"].lower() for n in names):
            pw(w)


def bigbig(wines):

    header("BIG BIG")
    units = ['magnum','imperial','jeroboam']
    names = ['jeroboam','magnum','imperial']
    
    for w in wines:
        if any(n in w["Name"].lower() for n in names) or any(u in w["Px"].lower() for u in units):
            pw(w)


def changes(wines):
    header("PRICE CHANGES")
    mask = "{x} => {y} per {z}, {a} {b}%"
    
    for w in wines:
        c = w["changes"]
        u = w['unchanged']
        name = u["Name"] if "Name" in u else c["Name"][1]
        pxUnit = u["Px Unit"] if "Px Unit" in u else c["Px Unit"][1]
        bulkUnit = u["Bulk Unit"] if "Bulk Unit" in u else c["Bulk Unit"][1]

        px = None
        if "Px" in c:
            px1 = float(c["Px"][0].replace('£',''))
            px2 = float(c["Px"][1].strip('£'))
            pxdelta = ((px2-px1)/px1)*100
            updown = "down" if pxdelta<=0 else "up"
            px = mask.format(x=c["Px"][0], y=c["Px"][1], z=pxUnit, a=updown, b = "%.1f" % abs(pxdelta))

        bpx = None
        if "Bulk Px" in c:
            px1 = float(c["Bulk Px"][0].replace('£','')) if len(c["Bulk Px"][0].strip()) >0 else 0.0
            px2 = float(c["Bulk Px"][1].strip('£')) if len(c["Bulk Px"][1].strip()) >0 else 0.0
            pxdelta = ((px2-px1)/px1)*100 if px1 != 0.0 else 0
            updown = "down" if pxdelta<=0 else "up"
            bpx = mask.format(x=c["Bulk Px"][0], y=c["Bulk Px"][1], z=bulkUnit, a=updown, b= "%.1f" % abs(pxdelta))

        
        if px is not None or bpx is not None:
            print(name.replace(',',''), px or '', bpx or '', sep=', ')    


def pall(wines, title):
    header(title)
    for w in wines:
        pw(w)

def diff_inventory(f1, f2):

    fullscan = False   
    f1 = 'empty.txt' if fullscan else f1

    delta = diff(f1, f2, 'Code')

    # todo: drive specials, bigbig, mispricing off load_csv(f2)

    specials(delta["added"])
    bigbig(delta["added"])

    changes(delta["changed"])
    
    pall(delta["added"],"NEW IN")
    pall(delta["removed"],"OUT OF STOCK")

    #with open('delta.json', 'w') as f:
    #    print(json.dumps(delta, indent = 4, sort_keys=True), file=f )

def main():
    
    f1 = sys.argv[1] if len(sys.argv) >= 3 else '20210911.csv'
    f2 = sys.argv[2] if len(sys.argv) >= 3 else '20210912.csv'  
    diff_inventory(f1, f2)


if __name__ == '__main__':
    main()
    