import { ChriscarlPage } from './app.po';

describe('chriscarl App', function() {
  let page: ChriscarlPage;

  beforeEach(() => {
    page = new ChriscarlPage();
  });

  it('should display message saying app works', () => {
    page.navigateTo();
    expect(page.getParagraphText()).toEqual('app works!');
  });
});
