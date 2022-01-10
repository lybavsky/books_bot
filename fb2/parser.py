import binascii
import hashlib
import xml.etree.ElementTree as ET
from io import BytesIO
import base64


from fb2.struct import FB2Structure



def parse_fb2(fb2job):
    fb2str = fb2job.get_str()
    if fb2str == "":
        fb2src = fb2job.get_path()
        f = open(fb2job.get_path(), 'rb')
        bs = f.read()
        f.close()

        hash = md5(bs)
    else:
        fb2src = BytesIO(fb2str)

        bs2src = BytesIO(fb2str)
        bs = bs2src.read()
        hash = md5(bs)

    el = ET.iterparse(fb2src)
    fb2struct = parse_fb2_it(el, fb2job)
    fb2struct.hash = hash

    return fb2struct


def parse_fb2_it(it, job):
    fb2 = FB2Structure(job)

    cover_filename = ""

    if it == None:
        return None

    for _, el in it:
        prefix, has_namespace, postfix = el.tag.partition('}')
        if has_namespace:
            el.tag = postfix  # strip all namespaces

    ar_root = it.root

    descr = ar_root.find("description")
    if descr == None:
        raise ValueError("can not find description")

    title_info = descr.find("title-info")
    if title_info == None:
        raise ValueError("can not find title-info")

    for title_field in title_info:
        if title_field.tag == "genre":
            fb2.add_genre(title_field.text)
        elif title_field.tag == "author":
            fnf = title_field.find("first-name")
            if fnf != None:
                fb2.set_first_name(fnf.text)
            lnf = title_field.find("last-name")

            if lnf != None:
                fb2.set_last_name(lnf.text)
        elif title_field.tag == "book-title":
            fb2.set_title(title_field.text)
        elif title_field.tag == "lang":
            fb2.set_lang(title_field.text)
        elif title_field.tag == "src-lang":
            fb2.set_src_lang(title_field.text)
        elif title_field.tag == "year":
            fb2.set_year(title_field.text)
        elif title_field.tag == "annotation":
            fb2.set_annotation(innertext(title_field))
        elif title_field.tag == "coverpage":
            im_link = title_field.find("image")
            if im_link != None:
                for attr in im_link.attrib:
                    if attr.split("}")[-1] == "href":
                        cover_filename = im_link.attrib[attr][1:]

    if cover_filename != "":
        cover_el = ar_root.find("binary[@id=\"" + cover_filename + "\"]")
        if cover_el != None:
            try:
                fb2.set_coverfile(cover_filename, base64.b64decode(cover_el.text))
            except binascii.Error:
                ()
    return fb2


def innertext(tag):
    return (tag.text or '') + ''.join(innertext(e) for e in tag) + (tag.tail or '')



def md5(bs):
    hash_object = hashlib.md5(bs)
    return hash_object.hexdigest()