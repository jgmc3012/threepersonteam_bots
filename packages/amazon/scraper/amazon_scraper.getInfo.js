() => {
    info = {
        'important': {},
        'additional' : []
    }
    
    rowsOfTables = document.querySelectorAll('#prodDetails tr')

    rowsOfTables.array.forEach( row => {
        name = row.children[0].innerText
        value = row.children[1].innerText
        switch (name) {
            case 'Dimensiones del producto':
                values = value.split(' ')
                info.important['dimensions'] = {
                    'dimensions': [
                        parseFloat(values[0]),
                        parseFloat(values[2]),
                        parseFloat(values[4])
                    ],
                    'units': values[5]
                }
                break;
            case 'Peso del producto':
                values = value.split(' ')
                info.important['product_weight'] = {
                    'weight': parseFloat(values[0]),
                    'units' : values[1]
                }
                break;
            case 'Peso del envío':
                values = value.split(' ')
                info.important['shipping_weight'] = {
                    'weight': parseFloat(values[0]),
                    'units' : values[1]
                }
                break;
            case 'Número de modelo del producto':
                info.important['model_number'] = value
                break;
            case 'ASIN':
                info.important['SKU'] = value
                break;
            default:
                //name.replace(new RegExp(' ', 'g'), '_')
                info.additional.push({'name': name, 'value': value})
                break;
        }
    })

    return info
}