import logging
import re
import yaml 


def price_or_err(pattern: str, string, value_default, pos=-1) -> str:
    """
    Este funcion recibe un patron con AL MENOS un grupo, una cadena de
    caracteres y una posicion del grupo que se desea retornar.

    En caso que el patron no se encuentre en la cadena retornara un value_default.
    """
    if string is None:
        return 0
    else:
        string = string.replace(',', '')
    match = re.search(pattern, string)
    if match:
        return match.groups()[pos]
    else:
        return value_default

def price_shipping_or_err(string, value_default) -> str:
    """
    Esta funcion recibe un string donde se buscara el texto 'FREE Shipping,\
    si lo encuentra retorna 0, de lo contrario retorna value_default.
    """
    if 'FREE Shipping' in string or 'Envío GRATIS' in string:
        return "0"
    else:
        return value_default

def weight_converter(quantity, unit:str)->float:
    converter = {
        'ounces': 0.0625,
        'ounce': 0.0625,
        'onzas': 0.0625,
        'onza': 0.0625,
        'oz': 0.0625,
        'pounds': 1,
        'pound': 1,
        'libras': 1,
        'libra': 1,
        'kilograms':2.20462,
        'kilogram':2.20462,
        'kilogramos':2.20462,
        'kilogramo':2.20462,
        'gramos':0.00220462,
        'gramo':0.00220462,
        'gr':0.00220462,
        'g':0.00220462,

    }
    return converter[unit.lower()]*float(quantity)

def distance_converter(quantity, unit:str)->float:
    converter = {
        'inches': 1,
        'inche': 1,
        'pulgadas': 1,
        'pulgada': 1,
        'in': 1,
        'centimeters':0.393701,
        'centimeter':0.393701,
        'centimetros':0.393701,
        'centimetro':0.393701,
        'cm':0.393701,
    }
    return converter[unit.lower()]*float(quantity)

def get_yaml(path:str)->dict:
    with open(path, 'r') as stream:
        response = yaml.load(stream)
    return response