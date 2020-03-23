$(document).tooltip();

$(function () {
	let selectedSkillsToDownload = [];
	let skillStatuses = {};

	function skillStatus(skill) {
		$.ajax({
			url: '/skills/checkInstallStatus/',
			data: {
				'skill': skill
			},
			type: 'POST'
		}).done(function (status) {
			skillStatuses[skill] = JSON.stringify(status).trim();
		}).fail(function () {
			skillStatuses[skill] = 'failed';
		});
	}

	function checkInstallStatus(skill) {
		skillStatus(skill);

		let status = skillStatuses[skill];
		if (status == JSON.stringify('installed')) {
			$('#' + skill + 'InstallTile').remove();
		} else if (status == JSON.stringify('failed') || status == JSON.stringify('unknown')) {
			$('#' + skill + 'InstallTile').children('.skillStoreSkillWaitAnimation').hide();
			$('#' + skill + 'InstallTile').children('.skillStoreSkillDownloadFail').css('display', 'flex');
		} else {
			setTimeout(function () {
				checkInstallStatus(skill);
			}, 5000);
		}
	}

	function checkUpdateStatus(skill, $skillContainer) {
		skillStatus(skill);
		let status = skillStatuses[skill];

		if (status == JSON.stringify('updated')) {
			$skillContainer.hide();
			$('#' + $skillContainer.attr('id') + '_animation').hide();
		} else if (status == JSON.stringify('failed') || status == JSON.stringify('unknown')) {
			$('#' + $skillContainer.attr('id') + '_animation').hide();
			$skillContainer.hide();
		} else {
			setTimeout(function () {
				checkUpdateStatus(skill, $skillContainer);
			}, 5000);
		}
	}

	function addToStore(installer) {
		if ($('#skillsPane').find('#' + installer['name'] + '-' + installer['author']).length === 0) {
			let $tile = $('<div class="skillStoreSkillTile" id="' + installer['name'] + 'InstallTile">' +
				'<div class="skillsStoreSkillTitle">' + installer['name'] + '</div>' +
				'<div class="skillsStoreSkillInfoContainer">' +
				'<div class="skillsStoreSkillLeft">' +
				'<div class="skillsStoreSkillAuthor"><i class="fas user-cog"></i> ' + installer['author'] + '</div>' +
				'<div class="skillsStoreSkillVersion"><i class="fas fa-code-branch" style="margin-right: 3px;"></i> ' + installer['version'] + '</div>' +
				'<div class="skillsStoreSkillCategory"><i class="fas fa-tags"></i> ' + installer['category'] + '</div>' +
				'</div>' +
				'<div class="skillsStoreSkillRight">' +
				'<i class="' + installer['icon'] + '" aria-hidden="true"></i>' +
				'</div>' +
				'</div>' +
				'<div class="skillStoreSkillDescription">' + installer['desc'] + '</div>' +
				'</div>');

			let $button = $('<div class="skillStoreSkillSelected skillStoreSkillButtonAnimation"><i class="fas fa-shopping-cart"></i></div>');
			$button.on('click touchstart', function () {
				$(this).hide();
				$(this).parent().children('.skillStoreSkillDownloadButton').show();
				for (let i = 0; i < selectedSkillsToDownload.length; i++) {
					if (selectedSkillsToDownload[i]['skill'] == installer['name']) {
						selectedSkillsToDownload.splice(i, 1);
						break;
					}
				}
				if (selectedSkillsToDownload.length <= 0) {
					$('#applySkillStore').hide();
				}
				return false;
			});
			$tile.append($button);

			$button = $('<div class="skillStoreSkillDownload skillStoreSkillDownloadButton"><i class="fas fa-download"></i></div>');
			$button.on('click touchstart', function () {
				$(this).hide();
				$(this).parent().children('.skillStoreSkillSelected').css('display', 'flex');
				selectedSkillsToDownload.push({'skill': installer['name'], 'author': installer['author']});
				$('#applySkillStore').show();
				return false;
			});
			$tile.append($button);

			$button = $('<div class="skillStoreSkillWaitAnimation skillStoreSkillButtonAnimation"><i class="fas fa-spinner fa-spin"></i></div>');
			$tile.append($button);

			$button = $('<div class="skillStoreSkillDownloadFail skillStoreSkillButtonAnimation"><i class="fas fa-exclamation-triangle"></i></div>');
			$tile.append($button);

			$('#skillsStore').append($tile);
		}
	}

	function loadStoreData() {
		$.ajax({
			url: '/skills/loadStoreData/',
			type: 'POST'
		}).done(function (answer){
			$('#skillStoreWait').hide();
			$.each(answer, function(skillName, installer){
				addToStore(installer);
			});
		});
	}

	$('#applySkillStore').on('click touchstart', function () {
		$('.skillStoreSkillSelected').hide();
		$(this).hide();
		$.each(selectedSkillsToDownload, function (index, skill) {
			$('#' + skill['skill'] + 'InstallTile').children('.skillStoreSkillWaitAnimation').css('display', 'flex');
		});

		$.ajax({
			url: '/skills/installSkills/',
			data: JSON.stringify(selectedSkillsToDownload),
			contentType: 'application/json',
			dataType: 'json',
			type: 'POST'
		}).done(function () {
		}).then(function () {
			$.each(selectedSkillsToDownload, function (index, skill) {
				setTimeout(function () {
					checkInstallStatus(skill['skill']);
				}, 10000);
			});
		});
		return false;
	});

	$('[id^=toggle_]').on('click touchstart', function () {
		$.ajax({
			url: '/skills/toggleSkill/',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
		});
		return false;
	});

	$('[id^=config_for_]').dialog({
		autoOpen: false,
		draggable: false,
		width: 600,
		height: 600,
		modal: true,
		resizable: false
	});

	$('[id^=update_]').on('click touchstart', function () {
		let $self = $(this);
		$.ajax({
			url: '/skills/updateSkill/',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			$self.hide();
			$('#' + $self.attr('id') + '_animation').show();
			setTimeout(function () {
				checkUpdateStatus($self.attr('id').split('_')[2], $self);
			}, 12000);
		});
		return false;
	});

	$('.skillSettings').on('click touchstart', function () {
		$('#config_for_' + $(this).attr('data-forSkill')).dialog('open');
		return false;
	});

	$('.skillViewIntents').on('click touchstart', function () {
		$(this).parent('.skillDefaultView').css('display', 'none');
		$(this).parent().parent().children('.skillIntentsView').css('display', 'flex');
		return false;
	});

	$('.skillIntentsViewCloseButton').on('click touchstart', function () {
		$(this).parent().parent().children('.skillDefaultView').css('display', 'flex');
		$(this).parent('.skillIntentsView').css('display', 'none');
		return false;
	});

	$('[id^=delete_]').on('click touchstart', function () {
		$.ajax({
			url: '/skills/deleteSkill/',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
		});
		return false;
	});

	$('[id^=reload_]').on('click touchstart', function () {
		$.ajax({
			url: '/skills/reloadSkill/',
			data: {
				id: $(this).attr('id')
			},
			type: 'POST'
		}).done(function () {
			location.reload();
		});
		return false;
	});

	$('#openSkillStore').on('click touchstart', function () {
		loadStoreData();
		$('#skillsPane').hide();
		$('#skillsStore').css('display', 'flex');
		$('#openSkillStore').hide();
		$('#closeSkillStore').show();
		return false;
	});

	$('#closeSkillStore').on('click touchstart', function () {
		location.reload();
		return false;
	});

	$('#applySkillStore').hide();
});
