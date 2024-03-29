
// ./env.js: const APIKEY = '*************'
var checkbcode = '';
const goodAudio = new Audio("/mp3/ding-idea-40142.mp3");  // https://pixabay.com/sound-effects/ding-idea-40142/
const badAudio = new Audio("/mp3/invalid-selection-39351.mp3");   // https://pixabay.com/sound-effects/invalid-selection-39351/
const tadaAudio = new Audio("/mp3/tada-fanfare-a-6313.mp3");  // https://pixabay.com/sound-effects/tada-fanfare-a-6313/
const barcodeScanner = new Html5QrcodeScanner(
  "barcode_scanner",
  {
    fps: 10,
    qrbox: { width: 300, height: 150 },
    supportedScanTypes: [Html5QrcodeScanType.SCAN_TYPE_CAMERA],
    aspectRatio: 0.5,
  }
);

// Listen for a barcode to be entered
document.getElementById("bcode").addEventListener("keypress", function (e) {
  if (e.key === 'Enter') {
    let barcode = document.getElementById('bcode').value;
    check_barcode(barcode);
  }
});

document.getElementById("manualButton").addEventListener("click", function (e) {
  let barcode = document.getElementById('bcode').value;
  check_barcode(barcode);
});

document.getElementById("admitButton").addEventListener("click", function (e) {
  check_in();
});

document.getElementById("abortButton").addEventListener("click", function (e) {
  abort();
});

// Listen for quicket flush click
document.getElementById("fqc").addEventListener("click", function (e) {
  document.getElementById('spinspin').className = 'spinning';
  flush_quicket();
  document.getElementById('spinspin').className = 'hidden';
});

// make sure cursor is in text box on load
window.onload = function () {
  reset_form();
  barcodeScanner.render((barcode) => {
    document.getElementById("bcode").value = barcode;
    barcodeScanner.pause(true);
    check_barcode(barcode);
  });
};


// *********
// FUNCTIONS
// *********

function flush_quicket() {
  let postdata = { 'session': APIKEY };
  var purl = 'https://checkin.goingnowhere.org:2443/flushcache';

  jQuery.ajax({
    url: purl,
    timeout: 10000,
    cache: 'false',
    crossDomain: true,
    dataType: 'json',
    type: "POST",
    data: postdata,

    success: function (data) {
      console.log('flushed away');
    },
    error: function (request, status, error) {
      alert(request.responseText);
    }
  });
}

function reset_form() {
  document.getElementById("admitButton").disabled = true;
  document.getElementById("bcode").value = "";

  change_colour('white');
  document.getElementById('scanpage').className = 'infoblock';
  document.getElementById('idcheck').className = 'hidden';
  document.getElementById('errordiv').className = 'hidden';
  document.getElementById('xxcheck').className = 'hidden';
  document.getElementById('spinspin').className = 'hidden';

  try { barcodeScanner.resume(); } catch { }
  $("#bcode").focus();
}

function abort() {
  console.log("Aborted!")
  reset_form();
}

function check_in() {
  var barcode = document.getElementById('bcode').value;
  console.log("Admitted one: " + barcode);

  var postdata = {
    'session': APIKEY,
    'barcode': barcode
  };
  var purl = 'https://checkin.goingnowhere.org:2443/checkin'

  jQuery.ajax({
    url: purl,
    cache: 'false',
    crossDomain: true,
    dataType: 'json',
    type: "POST",
    data: postdata,

    success: function (data) {
      //valid ticket
      console.log(data);
      if (data === 'CHECKEDIN') {
        //set the correct text in divs
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'hidden';
        document.getElementById('xxcheck').className = 'hidden';
        change_colour('green');
        setTimeout(reset_form, 2000);
        tadaAudio.play();
        document.getElementById('bcode').value = '';

      } else if (data === 'FAIL') {
        document.getElementById('errorclass').innerHTML = "Check in error!";
        document.getElementById('errorsolution').innerHTML = data['Message'];
        document.getElementById('scanpage').className = 'hidden';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        document.getElementById('xxcheck').className = 'hidden';
        change_colour('red');
        setTimeout(function () { change_colour('white'); }, 3000);
        badAudio.play();

      } else {
        document.getElementById('errorclass').innerHTML = "Ticket isn't valid!";
        document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " isn't valid. Please ask the gate lead to investigate further."
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        document.getElementById('xxcheck').className = 'hidden';
        change_colour('red');
        setTimeout(function () { change_colour('white'); }, 3000);
        badAudio.play();
      }
      document.getElementById('spinspin').className = 'hidden';

    },
    error: function (request, status, error) {
      alert("Something went wrong with the API call - probably the wifi is down.");
    }
  });
  $("#bcode").focus();
}

// retrieve name and ID for barcode
function check_barcode(barcode) {
  //spin while waiting
  document.getElementById('spinspin').className = 'spinning';

  var postdata = {
    'session': APIKEY,
    'barcode': barcode
  };
  var purl = 'https://checkin.goingnowhere.org:2443/barcode'
  jQuery.ajax({
    url: purl,
    cache: 'false',
    crossDomain: true,
    dataType: 'json',
    type: "POST",
    data: postdata,

    success: function (data) {
      //valid ticket
      console.log(data);

      if (data['CI'] === 'No' && data['state'] !== 'fail') {
        //set the correct text in divs
        console.log('matched');
        document.getElementById('idname').innerHTML = data['Name'];
        document.getElementById('idid').innerHTML = data['ID'];
        document.getElementById('scanpage').className = 'hidden';
        document.getElementById('errordiv').className = 'hidden';
        document.getElementById('idcheck').className = 'infoblock';
        document.getElementById("admitButton").disabled = false;
        $("#admitButton").focus();

        // CHECK IF THIS IS A CHILDREN TICKET
        if (data['Type'] === 'Children under 14') {
          document.getElementById('extra_check').innerHTML = "This is a childrens ticket - please check birthday is after 4 July 2008";
          document.getElementById('xxcheck').className = 'txtblock';
          change_colour('yellow');
          setTimeout(function () { change_colour('white'); }, 3000);
          goodAudio.play();

          // CHECK IF THIS IS A 14-18 TICKET
        } else if (data['Type'] === '14 to 18 y.o.') {
          document.getElementById('extra_check').innerHTML = "This is a 14-18 age ticket - please check birthday is after 4 July 2004";
          document.getElementById('xxcheck').className = 'txtblock';
          change_colour('yellow');
          setTimeout(function () { change_colour('white'); }, 3000);
          goodAudio.play();

          // CHECK IF THIS IS A CARER
        } else if (data['Type'] === 'Carer') {
          document.getElementById('extra_check').innerHTML = "This is a carer ticket. Director required for waiver. Please radio for director.";
          document.getElementById('xxcheck').className = 'txtblock';
          change_colour('yellow');
          setTimeout(function () { change_colour('white'); }, 3000);
          goodAudio.play();

          // CHECK IF THIS IS AN ART TICKET
        } else if (data['Type'] === 'Donation for Arts') {
          document.getElementById('errorclass').innerHTML = "THIS IS NOT A VALID TICKET.";
          document.getElementById('errorsolution').innerHTML = "It is an art donation. Please ask the person to supply their actual ticket. If they don't have one, please consult the gate lead.";
          document.getElementById('scanpage').className = 'infoblock';
          document.getElementById('idcheck').className = 'hidden';
          document.getElementById('errordiv').className = 'infoblock';
          change_colour('red');
          setTimeout(reset_form, 3000);
          badAudio.play();

          // CHECK IF THIS IS A FAILED EE ENTRY
        } else if (data['Type'] === 'Donation for Arts') {
          document.getElementById('errorclass').innerHTML = "THIS IS NOT A VALID TICKET.";
          document.getElementById('errorsolution').innerHTML = "It is an art donation. Please ask the person to supply their actual ticket. If they don't have one, please consult the gate lead.";
          document.getElementById('scanpage').className = 'infoblock';
          document.getElementById('idcheck').className = 'hidden';
          document.getElementById('errordiv').className = 'infoblock';
          change_colour('red');
          setTimeout(reset_form, 3000);
          badAudio.play();
        } else {
          goodAudio.play();
        }

      } else if (data['CI'] === 'Yes') {
        document.getElementById('errorclass').innerHTML = "Ticket already scanned!";
        document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " was already scanned on " + data['CIdate'] + " at " + data['CIstation'] + ". Name on the ticket is " + data['Name']
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        change_colour('red');
        setTimeout(reset_form, 3000);
        badAudio.play();

      } else if (data['state'] === 'fail') {
        document.getElementById('errorclass').innerHTML = data['reason']
        document.getElementById('errorsolution').innerHTML = "Consult the gate lead or gate handbook"
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        change_colour('red');
        setTimeout(reset_form, 3000);
        badAudio.play();

      } else {
        if (data.hasOwnProperty('status')) {
          document.getElementById('errorclass').innerHTML = data['status'];
          document.getElementById('errorsolution').innerHTML = "";
        } else {
          document.getElementById('errorclass').innerHTML = "Ticket isn't valid!";
          document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " isn't valid. Please ask the gate lead to investigate further."
        }
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        change_colour('red');
        setTimeout(reset_form, 3000);
        badAudio.play();
      }
    },
    error: function (request, status, error) {
      alert("Something went wrong with the API call - probably the wifi is down.");
      change_colour('red');
      setTimeout(reset_form, 3000);
      badAudio.play();
    }
  });

  document.getElementById('spinspin').className = 'hidden';
}


function change_colour(c) {
  console.log(c);
  let md = document.getElementById('mdiv');
  md.className = c;
  md.classList.add('eebody');
}

function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for (var i = 0; i < ca.length; i++) {
    var c = ca[i];
    while (c.charAt(0) == ' ') {
      c = c.substring(1);
    }
    if (c.indexOf(name) == 0) {
      return c.substring(name.length, c.length);
    }
  }
  return "";
}
