const assert=require('node:assert/strict');
const fs=require('node:fs');
const jsQR=require('../static/vendor/jsQR.js');
for(const name of ['ordinary','disguised']){
 const fixture=JSON.parse(fs.readFileSync(`${__dirname}/qr-${name}.json`));
 const result=jsQR(new Uint8ClampedArray(fixture.data),fixture.width,fixture.height);
 assert.equal(result.data,fixture.expected);console.log(`PASS: QR decode ${name}`);
}
assert.equal(jsQR(new Uint8ClampedArray(100*100*4).fill(255),100,100),null);
console.log('PASS: blank image does not decode');
