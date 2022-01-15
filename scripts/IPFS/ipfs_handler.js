const ipfsClient = require('ipfs-http-client');
const fs = require('fs');


module.exports.ipfs_pin_file = async function(filename) {
  const ipfs = ipfsClient.create({
    host: 'ipfs.infura.io',
    port: 5001,
    protocol: 'https',
  })
  
  const add_result = await ipfs.add(fs.readFileSync(filename))
  const hash = add_result.path
  console.log(hash)
  const pin_result = await ipfs.pin.add(hash)
}
