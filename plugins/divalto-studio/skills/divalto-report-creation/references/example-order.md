# Exemple complet et valide : report « Bon de commande »

Report imprimable pour une commande client, dérivé du fixture réel `src/test/fixtures/report/order.report.xml` (report shippé, produit par le designer WYSIWYG), simplifié aux sections et éléments essentiels pour rester lisible tout en couvrant les types les plus courants : `ReportHeader`, `PageHeader`, `Detail`, `ReportFooter`, `PageFooter`, et les éléments `Texte`, `Ligne`, `Forme`.

Fichiers : `Mobile/reports/order.report.xml` + `Mobile/reports/order.json`.

## `order.report.xml`

- `<Etat table="sw_data_orderheader">` : table principale du report, format A4, marges 20pt.
- `Section0` (`ReportHeader`) : imprimé une fois en tête — coordonnées société, type de document, n° de commande, date, nom client. `oh.orderheader_ID = '%row_ID%'` lie chaque section à l'enregistrement imprimé.
- `Section3` (`PageHeader`) : en-têtes de colonnes du tableau de lignes, répété sur chaque page (`nouvellePageAvant="true"`).
- `Lines` (`Detail`) : une ligne par ligne de commande (`sw_data_orderdetail`).
- `Total` (`ReportFooter`) : sous-total et total TTC, imprimés une fois en fin de report.
- `Section2` (`PageFooter`) : pagination et mentions légales, répété en bas de chaque page (`basDePage="true"`).

```xml
<?xml version="1.0" encoding="utf-8" standalone="yes"?>
<Etat table="sw_data_orderheader" margeLeft="20.00" margeTop="20.00" margeRight="20.00" margeBottom="20.00" format="A4">
  <Grille grilleLargeur="5" grilleHauteur="5" />
  <GlobalFont fontFamily="Tahoma" size="8.25" />
  <Section name="Section0" type="ReportHeader" height="139.83" visible="true" requete="SELECT ci.companyname AS 'ci.companyname', ci.address1 AS 'ci.address1', ci.city AS 'ci.city', cr.label AS documentTypeDefaultLabel, cr.translationKey AS 'lng:documentType:documentTypeDefaultLabel', oh.orderDate AS 'oh.orderDate', oh.customerOrderNumber AS 'oh.customerOrderNumber', c.name AS 'c.name'&#xD;&#xA;FROM sw_data_orderheader AS oh&#xD;&#xA;LEFT JOIN sw_data_confreport AS cr ON ( cr.confreport_ID = oh.confreport_ID )&#xD;&#xA;LEFT JOIN sw_data_customer AS c ON ( c.customer_ID = oh.customer_ID )&#xD;&#xA;LEFT JOIN sw_data_companyinfo AS ci ON ci.company_ID = oh.company_ID&#xD;&#xA;WHERE oh.orderheader_ID = '%row_ID%'">
    <Element name="Texte74" left="266.39" top="3.75" width="285.90" height="15.76" type="Texte">
      <Champ>ci.companyname</Champ>
      <Font fontFamily="Tahoma" size="12.00">
        <Bold />
      </Font>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte75" left="266.39" top="26.26" width="285.90" height="12.01" type="Texte">
      <Champ>ci.address1</Champ>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte78" left="266.39" top="41.27" width="285.90" height="12.01" type="Texte">
      <Champ>ci.city</Champ>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Forme2" left="0.00" top="60.06" width="556.05" height="34.52" type="Forme">
      <Forme>RoundedRectangle</Forme>
      <PenWidth>0.10</PenWidth>
      <Roundness>10.00</Roundness>
    </Element>
    <Element name="Texte24" left="3.75" top="63.81" width="113.31" height="12.01" type="Texte">
      <Champ>lng:documentType:documentTypeDefaultLabel</Champ>
      <Font fontFamily="Tahoma" size="8.25">
        <Bold />
      </Font>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte25" left="120.06" top="63.81" width="158.34" height="12.01" type="Texte">
      <Champ>oh.customerOrderNumber</Champ>
      <Font fontFamily="Tahoma" size="8.25">
        <Bold />
      </Font>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte29" left="281.40" top="63.81" width="87.05" height="12.01" type="Texte">
      <Texte>&lt;lng&gt;Gen_OrderDate&lt;/lng&gt; :</Texte>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte26" left="371.45" top="63.81" width="180.85" height="12.01" type="Texte">
      <Champ>oh.orderDate</Champ>
      <ContentAlignment>MiddleLeft</ContentAlignment>
      <FormatDate>d</FormatDate>
    </Element>
    <Element name="Texte17" left="3.75" top="97.06" width="180.85" height="12.01" type="Texte">
      <Champ>c.name</Champ>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
  </Section>
  <Section name="Section3" type="PageHeader" height="19.51" visible="true" nouvellePageAvant="true">
    <Element name="Texte50" left="0.00" top="0.00" width="180.85" height="19.51" type="Texte">
      <Texte>&lt;lng&gt;Gen_ProductDescription&lt;/lng&gt;</Texte>
      <Font fontFamily="Tahoma" size="8.25">
        <Bold />
      </Font>
      <ContentAlignment>MiddleCenter</ContentAlignment>
      <BackColor>-4144960</BackColor>
    </Element>
    <Element name="Texte52" left="183.85" top="0.00" width="42.02" height="19.51" type="Texte">
      <Texte>&lt;lng&gt;Gen_Quantity_Short&lt;/lng&gt;</Texte>
      <Font fontFamily="Tahoma" size="8.25">
        <Bold />
      </Font>
      <ContentAlignment>MiddleCenter</ContentAlignment>
      <BackColor>-4144960</BackColor>
    </Element>
    <Element name="Texte57" left="228.87" top="0.00" width="60.78" height="19.51" type="Texte">
      <Texte>&lt;lng&gt;Gen_Total&lt;/lng&gt;</Texte>
      <Font fontFamily="Tahoma" size="8.25">
        <Bold />
      </Font>
      <ContentAlignment>MiddleRight</ContentAlignment>
      <BackColor>-4144960</BackColor>
    </Element>
  </Section>
  <Section name="Lines" type="Detail" height="12.01" visible="true" requete="SELECT od.orderdetail_ID, od.productDescription AS productDescription, od.quantity AS quantity, od.amount AS amount&#xD;&#xA;FROM sw_data_orderdetail AS od&#xD;&#xA;WHERE od.orderheader_ID = '%row_ID%'&#xD;&#xA;ORDER BY od.lineNumber">
    <Element name="Ligne2" left="0.00" top="0.00" width="556.05" height="0.75" type="Ligne">
      <PenWidth>0.10</PenWidth>
      <PenColor>-4144960</PenColor>
    </Element>
    <Element name="Texte36" left="3.75" top="0.00" width="173.34" height="12.01" type="Texte">
      <Champ>productDescription</Champ>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte37" left="183.85" top="0.00" width="42.02" height="12.01" type="Texte">
      <Champ>quantity</Champ>
      <ContentAlignment>MiddleRight</ContentAlignment>
      <FormatNombre>@orderlineMaskQuantity</FormatNombre>
    </Element>
    <Element name="Texte41" left="228.87" top="0.00" width="60.78" height="12.01" type="Texte">
      <Champ>amount</Champ>
      <ContentAlignment>MiddleRight</ContentAlignment>
      <FormatNombre>@orderlineMaskAmount</FormatNombre>
    </Element>
  </Section>
  <Section name="Total" type="ReportFooter" height="86.30" visible="true" requete="SELECT h.subTotal AS subTotal, h.vatTotal AS vatTotal, h.grandTotal AS grandTotal&#xA;FROM sw_data_orderheader h&#xA;WHERE h.orderheader_ID = '%row_ID%'">
    <Element name="Ligne5" left="0.00" top="0.00" width="556.05" height="0.75" type="Ligne">
      <PenWidth>0.10</PenWidth>
      <PenColor>-4144960</PenColor>
    </Element>
    <Element name="Forme7" left="341.43" top="3.75" width="214.62" height="49.53" type="Forme">
      <Forme>RoundedRectangle</Forme>
      <PenWidth>0.10</PenWidth>
      <Roundness>10.00</Roundness>
      <FillingColor>-4144960</FillingColor>
    </Element>
    <Element name="Texte62" left="345.19" top="7.50" width="120.82" height="12.01" type="Texte">
      <Texte>&lt;lng&gt;Gen_Subtotal&lt;/lng&gt; :</Texte>
      <Font fontFamily="Tahoma" size="9.75" />
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte59" left="469.00" top="7.50" width="83.30" height="12.01" type="Texte">
      <Champ>subTotal</Champ>
      <Font fontFamily="Tahoma" size="9.75" />
      <ContentAlignment>MiddleRight</ContentAlignment>
      <FormatNombre>@orderheaderMaskTotal</FormatNombre>
    </Element>
    <Element name="Texte64" left="345.19" top="37.52" width="120.82" height="12.01" type="Texte">
      <Texte>&lt;lng&gt;Gen_GrandTotal&lt;/lng&gt; :</Texte>
      <Font fontFamily="Tahoma" size="9.75">
        <Bold />
      </Font>
      <ContentAlignment>MiddleLeft</ContentAlignment>
    </Element>
    <Element name="Texte61" left="469.00" top="37.52" width="83.30" height="12.01" type="Texte">
      <Champ>grandTotal</Champ>
      <Font fontFamily="Tahoma" size="9.75">
        <Bold />
      </Font>
      <ContentAlignment>MiddleRight</ContentAlignment>
      <FormatNombre>@orderheaderMaskTotal</FormatNombre>
    </Element>
  </Section>
  <Section name="Section2" type="PageFooter" height="27.01" visible="true" basDePage="true" requete="SELECT ci.legalStatus AS 'ci.legalInfos'&#xD;&#xA;FROM sw_data_orderheader AS oh&#xD;&#xA;LEFT JOIN sw_data_companyinfo AS ci ON ci.company_ID = oh.company_ID&#xD;&#xA;WHERE oh.orderheader_ID = '%row_ID%'">
    <Element name="Ligne1" left="0.00" top="0.00" width="556.05" height="0.75" type="Ligne">
      <PenWidth>0.10</PenWidth>
    </Element>
    <Element name="Texte10" left="408.97" top="3.75" width="147.08" height="12.01" type="Texte">
      <Texte>%current_page% / %total_pages%</Texte>
      <ContentAlignment>MiddleRight</ContentAlignment>
    </Element>
    <Element name="Texte87" left="0.00" top="15.01" width="556.05" height="12.01" type="Texte">
      <Champ>ci.legalInfos</Champ>
      <Font fontFamily="Tahoma" size="6.00" />
      <ContentAlignment>MiddleCenter</ContentAlignment>
    </Element>
  </Section>
</Etat>
```

## `order.json`

```json
{
  "label": "Bon de commande",
  "reportType": "Order",
  "isDefault": true,
  "exportValue": null,
  "externalDocCode": null,
  "stub": null,
  "archiveMode": null,
  "archiveVersionsNumber": null,
  "translationKey": "Gen_Order"
}
```

> Cet exemple a été validé avec `validateReportXml` (le même parseur que le designer WYSIWYG) — résultat : **0 erreur**. Voir le workflow dans `../SKILL.md` § Workflow obligatoire, étape 5.
