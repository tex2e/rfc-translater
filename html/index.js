
console.log('hello!');

document.addEventListener('DOMContentLoaded', function () {

  var searchText = document.getElementById('searchText');

  if (searchText) {

    searchText.addEventListener('keyup', function (event) {
      event.preventDefault();
      if (event.isComposing || event.keyCode === 229) return;

      // Search RFC by user input
      var input, filter, listGroup, listItem, a, i, txtValue;
      input = document.getElementById('searchText');
      filter = input.value;
      listGroup = document.getElementById("RFCs");
      listItem = listGroup.getElementsByTagName('a');

      console.log(filter);

      // Loop through all list items, and hide those who don't match the search query
      for (i = 0; i < listItem.length; i++) {
        txtValue = listItem[i].textContent || listItem[i].innerText;
        if (txtValue.indexOf(filter) > -1) {
          listItem[i].style.display = "";
        } else {
          listItem[i].style.display = "none";
        }
      }
    });

    searchText.addEventListener('keypress', function (event) {
      var key = event.which || event.keyCode;
      if (key === 13) { // Enterキーでページをリロードさせない
        event.preventDefault();
      }
    });

  }

});
