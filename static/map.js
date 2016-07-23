var map;

var pGoStyle=[{"featureType":"landscape.man_made","elementType":"geometry.fill","stylers":[{"color":"#a1f199"}]},{"featureType":"landscape.natural.landcover","elementType":"geometry.fill","stylers":[{"color":"#37bda2"}]},{"featureType":"landscape.natural.terrain","elementType":"geometry.fill","stylers":[{"color":"#37bda2"}]},{"featureType":"poi.attraction","elementType":"geometry.fill","stylers":[{"visibility":"on"}]},{"featureType":"poi.business","elementType":"geometry.fill","stylers":[{"color":"#e4dfd9"}]},{"featureType":"poi.business","elementType":"labels.icon","stylers":[{"visibility":"off"}]},{"featureType":"poi.park","elementType":"geometry.fill","stylers":[{"color":"#37bda2"}]},{"featureType":"road","elementType":"geometry.fill","stylers":[{"color":"#84b09e"}]},{"featureType":"road","elementType":"geometry.stroke","stylers":[{"color":"#fafeb8"},{"weight":"1.25"}]},{"featureType":"road.highway","elementType":"labels.icon","stylers":[{"visibility":"off"}]},{"featureType":"water","elementType":"geometry.fill","stylers":[{"color":"#5ddad6"}]}];

var selectedStyle = 'light';

function initMap() {


    map = new google.maps.Map(document.getElementById('map'), {
        center: {
            lat: 40.783072,
            lng: -73.971193
        },
        zoom: 12,
        streetViewControl: false,
		mapTypeControl: true,
		mapTypeControlOptions: {
          style: google.maps.MapTypeControlStyle.DROPDOWN_MENU,
          mapTypeIds: [
              google.maps.MapTypeId.ROADMAP,
              'style_pgo']
        },
    });
	var style_pgo = new google.maps.StyledMapType(pGoStyle, {name: "PokemonGo"});
	map.mapTypes.set('style_pgo', style_pgo);

    map.addListener('maptypeid_changed', function(s) {
        localStorage['map_style'] = this.mapTypeId;
    });

    if (typeof localStorage['map_style'] != undefined && localStorage['map_style'] != 'undefined')
	   map.setMapTypeId(localStorage['map_style']);

};


function pokemonLabel(name, id, disappear_time, latitude, longitude) {
    disappear_date = new Date(disappear_time)
    var pad = function (number) { return number <= 99 ? ("0" + number).slice(-2) : number; }

    var contentstring = `
        <div>
            <b>${name}</b>
            <span> - </span>
            <small>
                <a href='http://www.pokemon.com/us/pokedex/${id}' target='_blank' title='View in Pokedex'>#${id}</a>
            </small>
        </div>
        <div>
            Disappears at ${pad(disappear_date.getHours())}:${pad(disappear_date.getMinutes())}:${pad(disappear_date.getSeconds())}
            <span class='label-countdown' disappears-at='${disappear_time}'>(00m00s)</span></div>
        <div>
            <a href='https://www.google.com/maps/dir/Current+Location/${latitude},${longitude}'
                    target='_blank' title='View in Maps'>Get directions</a>
        </div>`;
    return contentstring;
};

// Dicts
map_pokemons = {} // Pokemon

function setupPokemonMarker(item) {
    var marker = new google.maps.Marker({
        position: {
            lat: item.latitude,
            lng: item.longitude
        },
        map: map,
        icon: 'static/icons/' + item.pokemon_id + '.png'
    });

    marker.infoWindow = new google.maps.InfoWindow({
        content: pokemonLabel(item.pokemon_name, item.pokemon_id, item.disappear_time, item.latitude, item.longitude)
    });

    addListeners(marker);
    return marker;
};

function addListeners(marker) {
    marker.addListener('click', function() {
        marker.infoWindow.open(map, marker);
        updateLabelDiffTime();
        marker.persist = true;
    });

    google.maps.event.addListener(marker.infoWindow, 'closeclick', function() {
        marker.persist = null;
    });

    marker.addListener('mouseover', function() {
        marker.infoWindow.open(map, marker);
        updateLabelDiffTime();
    });

    marker.addListener('mouseout', function() {
        if (!marker.persist) {
            marker.infoWindow.close();
        }
    });
    return marker
};

function clearStaleMarkers() {
    $.each(map_pokemons, function(key, value) {

        if (map_pokemons[key]['disappear_time'] < new Date().getTime()) {
            map_pokemons[key].marker.setMap(null);
            delete map_pokemons[key];
        }
    });
};

function updateMap() {
    $.ajax({
        url: "raw_data",
        type: 'GET',
        data: {
            'pokemon': document.getElementById('pokemon-switch').checked,
        },
        dataType: "json"
    }).done(function(result) {

      $.each(result.pokemons, function(i, item){
          if (!document.getElementById('pokemon-switch').checked) {
              return false; // in case the checkbox was unchecked in the meantime.
          }
          if (!(item.encounter_id in map_pokemons)) {
              // add marker to map and item to dict
              if (item.marker) item.marker.setMap(null);
              item.marker = setupPokemonMarker(item);
              map_pokemons[item.encounter_id] = item;
          }

      });

        clearStaleMarkers();
    });
};

window.setInterval(updateMap, 5000);
updateMap();

$('#pokemon-switch').change(function() {
    if (this.checked) {
        updateMap();
    } else {
        $.each(map_pokemons, function(key, value) {
            map_pokemons[key].marker.setMap(null);
        });
        map_pokemons = {}
    }
});

var updateLabelDiffTime = function() {
    $('.label-countdown').each(function(index, element) {
        var disappearsAt = new Date(parseInt(element.getAttribute("disappears-at")));
        var now = new Date();

        var difference = Math.abs(disappearsAt - now);
        var hours = Math.floor(difference / 36e5);
        var minutes = Math.floor((difference - (hours * 36e5)) / 6e4);
        var seconds = Math.floor((difference - (hours * 36e5) - (minutes * 6e4)) / 1e3);

        if (disappearsAt < now) {
            timestring = "(expired)";
        } else {
            timestring = "(";
            if (hours > 0)
                timestring = hours + "h";

            timestring += ("0" + minutes).slice(-2) + "m";
            timestring += ("0" + seconds).slice(-2) + "s";
            timestring += ")";
        }

        $(element).text(timestring)
    });
};

window.setInterval(updateLabelDiffTime, 1000);
