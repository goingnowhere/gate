var sescookie = getCookie('eesession');
var checkbcode = '';
const goodaudio = new Audio("https://app.goingnowhere.org/sounds/cp.wav");
const badaudio = new Audio("https://app.goingnowhere.org/sounds/ysnp.wav");
var sessionkey = 'SET_THIS_BEFORE_USER';

// Listen for a barcode to be entered
document.getElementById("bcode").addEventListener("keypress", function (e) {
  if (e.key === 'Enter') {
    let rawtext = document.getElementById('bcode').value;
    document.getElementById('bcode').value = '';
    document.getElementById('current_bcode').value = rawtext;
    //spin while waiting
    document.getElementById('spinspin').className = 'spinning';
    check_barcode(rawtext);
  }
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

// Listen for cache flush click
document.getElementById("fsc").addEventListener("click", function (e) {
  flush_cache();
});

// Listen for quicket flush click
document.getElementById("fqc").addEventListener("click", function (e) {
  flush_quicket();
});

// make sure cursor is in text box on load
window.onload = function() {
  $("#bcode").focus();
};


// *********
// FUNCTIONS
// *********

function flush_quicket() {
  let postdata = {'session': sessionkey};
  var purl = 'https://eeapi.goingnowhere.org:2443/flushcache';

  jQuery.ajax({
    url: purl,
    cache: 'false',  
    crossDomain: true,
    dataType: 'json',
    type: "POST",
    data: postdata,

    success: function(data) {
      console.log('flushed away');
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
    setTimeout(function() {change_colour('white'); }, 3000);
    document.getElementById('spinspin').className = 'hidden';
    badaudio.play();
    return;
  }
  var postdata = {'session': sessionkey,
                  'barcode': barcode};
  var purl = 'https://eeapi.goingnowhere.org:2443/checkin'

  jQuery.ajax({
    url: purl,
    cache: 'false', 
    crossDomain: true,
    dataType: 'json',
    type: "POST",
    data: postdata,

    success: function(data) {
      //valid ticket
      console.log(data);
      if (data === 'FAIL') {
        //set the correct text in divs
	document.getElementById('scanpage').className = 'infoblock';
	document.getElementById('idcheck').className = 'hidden';
	document.getElementById('errordiv').className = 'hidden';
	change_colour('green');
	setTimeout(function() {change_colour('white'); }, 3000);
        goodaudio.play();
      } else if (data === 'CHECKEDIN') {
	document.getElementById('errorclass').innerHTML = "Check in error!";
	document.getElementById('errorsolution').innerHTML = data['Message'];
	document.getElementById('scanpage').className = 'hidden';
	document.getElementById('idcheck').className = 'hidden';
	document.getElementById('errordiv').className = 'infoblock';
	change_colour('red');
	setTimeout(function() {change_colour('white'); }, 3000);
        badaudio.play();

      } else {
	document.getElementById('errorclass').innerHTML = "Ticket isn't valid!";
	document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " isn't valid. Please ask the gate lead to investigate further."
	document.getElementById('scanpage').className = 'infoblock';
	document.getElementById('idcheck').className = 'hidden';
	document.getElementById('errordiv').className = 'infoblock';
	change_colour('red');
	setTimeout(function() {change_colour('white'); }, 3000);
        badaudio.play();
      }
      document.getElementById('spinspin').className = 'hidden';
        
    }
  });
}

// retrieve name and ID for barcode
function check_barcode(barcode) {
  
  var postdata = {'session': sessionkey,
                  'barcode': barcode};
  var purl = 'https://eeapi.goingnowhere.org:2443/barcode'
  jQuery.ajax({
    url: purl,
    cache: 'false', 
    crossDomain: true,
    dataType: 'json',
    type: "POST",
    data: postdata,

    success: function(data) {
      //valid ticket
      console.log(data);
      if (data['CI'] === 'No') {
        //set the correct text in divs
	console.log('matched');
	document.getElementById('idname').innerHTML = data['Name'];
	document.getElementById('idid').innerHTML = data['ID'];
	document.getElementById('scanpage').className = 'hidden';
	document.getElementById('errordiv').className = 'hidden';
	document.getElementById('idcheck').className = 'infoblock';
        document.getElementById('current_bcode').value = barcode;
        $("#verifybcode").focus();
      } else if (data['CI'] === 'Yes') {
	document.getElementById('errorclass').innerHTML = "Ticket already scanned!";
	document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " was already scanned on " + data['CIdate'] + " at " + data['CIstation'] + ". Name on the ticket is " + data['Name']
	document.getElementById('scanpage').className = 'infoblock';
	document.getElementById('idcheck').className = 'hidden';
	document.getElementById('errordiv').className = 'infoblock';
	change_colour('red');
	setTimeout(function() {change_colour('white'); }, 3000);
        badaudio.play();
      } else {
	document.getElementById('errorclass').innerHTML = "Ticket isn't valid!";
	document.getElementById('errorsolution').innerHTML = "Ticket with barcode " + barcode + " isn't valid. Please ask the gate lead to investigate further."
	document.getElementById('scanpage').className = 'infoblock';
	document.getElementById('idcheck').className = 'hidden';
	document.getElementById('errordiv').className = 'infoblock';
	change_colour('red');
	setTimeout(function() {change_colour('white'); }, 3000);
        badaudio.play();
      }
      document.getElementById('spinspin').className = 'hidden';
        
    }
  });
}


function change_colour(c) {
  let md = document.getElementById('mdiv');
  md.className = c;
  md.classList.add('eebody');
}

function getCookie(cname) {
  var name = cname + "=";
  var decodedCookie = decodeURIComponent(document.cookie);
  var ca = decodedCookie.split(';');
  for(var i = 0; i <ca.length; i++) {
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
