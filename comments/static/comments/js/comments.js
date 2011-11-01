function addAjaxCommentsForm(formid) {
    $('#' + formid + ' form').ajaxForm({
        success: function(data, form, opts) {
            if (data.state == 'form') {
                $('#' + formid + ' .xcomment_new').html(data.html)
                addAjaxCommentsForm(formid)
            } else if (data.state == 'comment') {
                var $html = $('<div/>').html(data.html)
                $('#' + formid + ' .xcomment_new').attr('id', $html.find('.xcomments_comment').attr('id') + '_place').html($html.filter('div:first').html())
                $('#' + formid + ' .xcomment_new').parent().append($('#' + formid + ' .xcomment_new'))
                $('#' + formid + ' .xcomment_new').removeClass('xcomment_new').addClass('new_xcomment')
            } else if (data.state == 'error') {
                sayError(data.html)
            }
        },
        error: function(date) {
            sayError('Unknown Error')
        }
    })
}

$(document).ready(function() {
    $('#xcomments .xcomments_moderate').live('click', function() {
        var pressed = $(this)
        $.ajax({
            url: pressed.attr('href'),
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                if (data.state == 'success') {
                    hideComment(pressed)
                }
            }
        })
        return false;
    })
    $('#xcomments .xcomments_rate').live('click', function() {
        var pressed = $(this)
        $.ajax({
            url: pressed.attr('href'),
            type: 'POST',
            dataType: 'json',
            success: function(data) {
                if (data.state == 'success') {
                    pressed.parent().children('.xcomments_rating').text(data.rating)
                    rateComment(pressed, data.rating)
                }
            }
        })
        return false;
    })
    $('#xcomments .xcomments_comment').live('click', function() {
        var remove = $('#xcomments form').parent()
        if(remove.parent().find('li').length == 1) {
            remove.parent().remove()
        } else {
            remove.remove()
        }
        var pressed = $(this)
        $.ajax({
            url: pressed.attr('href'),
            type: 'POST',
            data: {
                'initial'     : '1',
                'object_pk'   : pressed.data('object_pk'),
                'content_type': pressed.data('content_type'),
                'parent'      : pressed.data('parent')
            },
            dataType: 'json',
            success: function(data) {
                if (data.state == 'form') {
                    if (pressed.attr('id') == 'xcomments_root') {
                        $('#' + pressed.attr('id') + '_place').append('<ul><li class="xcomment_new">' + data.html + '</li></ul>')
                    } else {
                        if ($('#' + pressed.attr('id') + '_place ul').length > 0) {
                            $('#' + pressed.attr('id') + '_place ul:first').prepend('<li class="xcomment_new">' + data.html + '</li>')
                        } else {
                            $('#' + pressed.attr('id') + '_place').append('<ul><li class="xcomment_new">' + data.html + '</li></ul>')
                        }
                    }
                    addAjaxCommentsForm(pressed.attr('id') + '_place')
                } else if (data.state == 'error') {
                    sayError(data.html)
                }
            },
            error: function(date) {
                sayError('Unknown Error')
            }
        })
        return false;
    })
})
