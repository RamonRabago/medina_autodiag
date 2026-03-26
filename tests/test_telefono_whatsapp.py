from app.utils.telefono_whatsapp import normalizar_para_whatsapp


def test_mx_10_digitos():
    assert normalizar_para_whatsapp("55 1234 5678") == "525512345678"


def test_mx_con_52():
    assert normalizar_para_whatsapp("+52 1 55 1234 5678") == "5215512345678"


def test_vacio():
    assert normalizar_para_whatsapp(None) is None
    assert normalizar_para_whatsapp("") is None
