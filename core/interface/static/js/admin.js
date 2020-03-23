$(document).tooltip();

$(function () {

	let locked = false;
	let $defaultTab = $('#adminPageTabsContainer ul li:first');
	$defaultTab.addClass('activeTab');

	function areYouReady($icon) {
		$.ajax({
			url: '/admin/areYouReady/',
			type: 'POST'
		}).done(function(response) {
			if (response['success']) {
				$icon.removeClass('red');
				$icon.addClass('green');
				setTimeout(function () {
					$icon.removeClass('green');
					$icon.removeClass('fa-spin');
					locked = false;
				}, 3000);
			} else {
				setTimeout(function () {
					areYouReady($icon);
				}, 1000);
			}
		}).fail(function() {
			setTimeout(function () {
				areYouReady($icon);
			}, 1000);
		});
	}

	function handleUtilityClick($div, endpoint, timeout) {
		if (locked) {
			return;
		}

		locked = true;
		let $icon = $div.children('.utilityIcon').children('i');
		$icon.addClass('fa-spin red');
		$.ajax({
			url: '/admin/' + endpoint + '/',
			type: 'POST'
		});
		setTimeout(function () {
			areYouReady($icon);
		}, timeout);
	}

	$('.tabsContent').children().each(function () {
		if ($(this).attr('id') == $defaultTab.data('for')) {
			$(this).show();
		}
		else {
			$(this).hide();
		}
	});

	$('.tab').on('click touchstart', function () {
		let target = $(this).data('for');
		$(this).addClass('activeTab');

		$('#adminPageTabsContainer ul li').each(function () {
			if ($(this).data('for') != target) {
				$(this).removeClass('activeTab');
			}
		});

		$('.tabsContent').children().each(function () {
			if ($(this).attr('id') == target) {
				$(this).show();
			}
			else {
				$(this).hide();
			}
		});
		return false;
	});

	$('#restart').on('click touchstart', function () {
		handleUtilityClick($(this), 'restart', 5000);
		return false;
	});

	$('#reboot').on('click touchstart', function () {
		handleUtilityClick($(this), 'reboot', 10000);
		return false;
	});

	$('#trainAssistant').on('click touchstart', function () {
		handleUtilityClick($(this), 'trainAssistant', 5000);
		return false;
	});

	$('#wipeAll').on('click touchstart', function () {
		handleUtilityClick($(this), 'wipeAll', 5000);
		return false;
	});

	$('#update').on('click touchstart', function () {
		handleUtilityClick($(this), 'updatee', 5000);
		return false;
	});

	$('#addUser').on('click touchstart', function () {
		handleUtilityClick($(this), 'addUser', 1000);
		return false;
	});

	$('#addWakeword').on('click touchstart', function () {
		handleUtilityClick($(this), 'addWakeword', 1000);
		return false;
	});

	$('#tuneWakeword').on('click touchstart', function () {
		handleUtilityClick($(this), 'tuneWakeword', 1000);
		return false;
	});
});
