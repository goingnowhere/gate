
window.onload = function () {
  resetForm();
  addEventListeners();
  barcodeScanner.render((barcode) => {
    document.getElementById("barcode").value = barcode;
    barcodeScanner.pause(true);
    checkBarcode(barcode);
  });
};

const barcodeScanner = new Html5QrcodeScanner(
  "barcodeScanner",
  {
    fps: 10,
    qrbox: { width: 300, height: 150 },
    supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
    aspectRatio: 0.5,
  }
);

function addEventListeners() {
  document.getElementById("barcode").addEventListener("keypress", function (e) {
    if (e.key === 'Enter') {
      let barcode = document.getElementById('barcode').value;
      checkBarcode(barcode);
    }
  });

  document.getElementById("manualButton").addEventListener("click", function (e) {
    let barcode = document.getElementById('barcode').value;
    checkBarcode(barcode);
  });
}


function resetForm() {
  document.getElementById("barcode").value = "";
  try { barcodeScanner.resume(); } catch { }
  document.getElementById("barcode").focus();
}
