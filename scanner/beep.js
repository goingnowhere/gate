var sescookie = getCookie('eesession');
var checkbcode = '';
const APIKEY = '<APIKEY>';
const goodaudio = new Audio("https://app.goingnowhere.org/sounds/boing.wav");
const badaudio = new Audio("https://app.goingnowhere.org/sounds/arggg.wav");
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

document.getElementById("manualbutton").addEventListener("click", function (e) {
  let barcode = document.getElementById('bcode').value;
  check_barcode(barcode);
});

// Listen for a barcode to be entered after ID check
document.getElementById("verifybcode").addEventListener("keypress", function (e) {
  if (e.key === 'Enter') {
    let rawtext = document.getElementById('verifybcode').value;
    document.getElementById('verifybcode').value = '';
    document.getElementById('spinspin').className = 'spinning';
    check_in(rawtext);
  }
});

// Listen for quicket flush click
document.getElementById("fqc").addEventListener("click", function (e) {
  document.getElementById('spinspin').className = 'spinning';
  flush_quicket();
  document.getElementById('spinspin').className = 'hidden';
});

// make sure cursor is in text box on load
window.onload = function () {
  document.getElementById("bcode").value = "";
  barcodeScanner.render((barcode) => {
    document.getElementById("bcode").value = barcode;
    barcodeScanner.pause(true);
    window.setTimeout(() => barcodeScanner.resume(), 2000);
    check_barcode(barcode);
  });
  $("#bcode").focus();
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


function check_in(barcode) {
  // do basic check to verify working with same barcode
  let checkbcode = document.getElementById('current_bcode').value;
  if (checkbcode !== barcode) {
    document.getElementById('errorclass').innerHTML = "Check in error!";
    document.getElementById('errorsolution').innerHTML = "Different barcode scanned! Please rescan initial barcode and verify ID and then scan it a second time to check in!";
    document.getElementById('scanpage').className = 'infoblock';
    document.getElementById('idcheck').className = 'hidden';
    document.getElementById('errordiv').className = 'infoblock';
    change_colour('red');
    setTimeout(function () { change_colour('white'); }, 3000);
    document.getElementById('spinspin').className = 'hidden';
    badaudio.play();
    return;
  }
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
        setTimeout(function () { change_colour('white'); }, 3000);
        goodaudio.play();
      } else if (data === 'FAIL') {
        document.getElementById('errorclass').innerHTML = "Check in error!";
        document.getElementById('errorsolution').innerHTML = data['Message'];
        document.getElementById('scanpage').className = 'hidden';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        document.getElementById('xxcheck').className = 'hidden';
        change_colour('red');
        setTimeout(function () { change_colour('white'); }, 3000);
        badaudio.play();

      } else {
        document.getElementById('errorclass').innerHTML = "Ticket isn't valid!";
        document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " isn't valid. Please ask the gate lead to investigate further."
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        document.getElementById('xxcheck').className = 'hidden';
        change_colour('red');
        setTimeout(function () { change_colour('white'); }, 3000);
        badaudio.play();
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

  document.getElementById('current_bcode').value = barcode;
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
        document.getElementById('current_bcode').value = barcode;
        $("#verifybcode").focus();

        // CHECK IF THIS IS A CHILDREN TICKET
        if (data['Type'] === 'Children under 14') {
          document.getElementById('extra_check').innerHTML = "This is a childrens ticket - please check birthday is after 4 July 2008";
          document.getElementById('xxcheck').className = 'txtblock';
          change_colour('yellow');
          setTimeout(function () { change_colour('white'); }, 3000);

          // CHECK IF THIS IS A 14-18 TICKET
        } else if (data['Type'] === '14 to 18 y.o.') {
          document.getElementById('extra_check').innerHTML = "This is a 14-18 age ticket - please check birthday is after 4 July 2004";
          document.getElementById('xxcheck').className = 'txtblock';
          change_colour('yellow');
          setTimeout(function () { change_colour('white'); }, 3000);

          // CHECK IF THIS IS A CARER
        } else if (data['Type'] === 'Carer') {
          document.getElementById('extra_check').innerHTML = "This is a carer ticket. Please check if they need Inclusion Team assistance and point them towards Malfare";
          document.getElementById('xxcheck').className = 'txtblock';
          change_colour('yellow');
          setTimeout(function () { change_colour('white'); }, 3000);

          // CHECK IF THIS IS AN ART TICKET
        } else if (data['Type'] === 'Donation for Arts') {
          document.getElementById('errorclass').innerHTML = "THIS IS NOT A VALID TICKET.";
          document.getElementById('errorsolution').innerHTML = "It is an art donation. Please ask the person to supply their actual ticket. If they don't have one, please consult the gate lead.";
          document.getElementById('scanpage').className = 'infoblock';
          document.getElementById('idcheck').className = 'hidden';
          document.getElementById('errordiv').className = 'infoblock';
          change_colour('red');
          setTimeout(function () { change_colour('white'); }, 3000);
          badaudio.play();

          // CHECK IF THIS IS A FAILED EE ENTRY
        } else if (data['Type'] === 'Donation for Arts') {
          document.getElementById('errorclass').innerHTML = "THIS IS NOT A VALID TICKET.";
          document.getElementById('errorsolution').innerHTML = "It is an art donation. Please ask the person to supply their actual ticket. If they don't have one, please consult the gate lead.";
          document.getElementById('scanpage').className = 'infoblock';
          document.getElementById('idcheck').className = 'hidden';
          document.getElementById('errordiv').className = 'infoblock';
          change_colour('red');
          setTimeout(function () { change_colour('white'); }, 3000);
          badaudio.play();
        }

      } else if (data['CI'] === 'Yes') {
        document.getElementById('errorclass').innerHTML = "Ticket already scanned!";
        document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " was already scanned on " + data['CIdate'] + " at " + data['CIstation'] + ". Name on the ticket is " + data['Name']
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        change_colour('red');
        setTimeout(function () { change_colour('white'); }, 3000);
        badaudio.play();

      } else if (data['state'] === 'fail') {
        document.getElementById('errorclass').innerHTML = data['reason']
        document.getElementById('errorsolution').innerHTML = "Consult the gate lead or gate handbook"
        document.getElementById('scanpage').className = 'infoblock';
        document.getElementById('idcheck').className = 'hidden';
        document.getElementById('errordiv').className = 'infoblock';
        change_colour('red');
        setTimeout(function () { change_colour('white'); }, 3000);
        badaudio.play();

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
        setTimeout(function () { change_colour('white'); }, 3000);
        badaudio.play();
      }

      document.getElementById('bcode').value = '';

    },
    error: function (request, status, error) {
      alert("Something went wrong with the API call - probably the wifi is down.");
      // don't clear input - user might want to retry
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
