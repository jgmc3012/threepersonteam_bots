()=>{
    desc = {}
    try {
        descBasic = document.getElementById('productDescription')
        desc['basic'] = `<div>${descBasic.innerHTML}</div>`
    } catch (error) {
        throw 'No se encontro la descripcion del producto'
    }

    try {
        descPlus = document.querySelector('#aplus > div')
        desc['plus'] = `<div>${descPlus.innerHTML}</div>`
    } catch {
    }

    return desc
}