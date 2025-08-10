close all

% Directorio donde están los CSV de resultados
resultsDir = 'results_spread_ids';  
csvFiles   = dir(fullfile(resultsDir, 'topo_*.csv'));

% Prealocar
numTopos     = length(csvFiles);
topoSizes    = zeros(numTopos,1);
meanSpread   = zeros(numTopos,1);
meanMST      = zeros(numTopos,1);
meanPSO      = zeros(numTopos,1);
meanGA       = zeros(numTopos,1);

% Leer cada CSV y calcular medias
for k = 1:numTopos
    fname = csvFiles(k).name;
    % Extraer número de nodos
    tok = regexp(fname, 'topo_(\d+)\.csv', 'tokens');
    n = str2double(tok{1}{1});
    topoSizes(k) = n;
    
    % Leer la tabla; ajusta los nombres de columna según tu CSV real
    T = readtable(fullfile(resultsDir,fname));
    meanSpread(k) = mean(T{:, 'SpreadIDs_s_'});  
    meanMST(k)    = mean(T{:, 'MST_s_'});        
    meanPSO(k)    = mean(T{:, 'PSO_s_'});        
    meanGA(k)     = mean(T{:, 'GA_s_'});         
end

% Ordenar por tamaño de topología
[topoSizes, idx] = sort(topoSizes);
meanSpread = meanSpread(idx);
meanMST    = meanMST(idx);
meanPSO    = meanPSO(idx);
meanGA     = meanGA(idx);

% Preparar nombres y datos
algos   = {'BLOSTE (Spread IDs)','MST','PSO','GA'};
data    = {meanSpread, meanMST, meanPSO, meanGA};
markers = {'o-','s-','d-','^-'};
colors  = lines(4);

% Crear figura
figure('Position',[100 100 1500 450]);
for i = 1:4
    ax = subplot(1,4,i);
    ax.FontSize = 14;
    y  = data{i};
    
    % Graficar datos medios
    p1 = plot(topoSizes, y, markers{1}, 'LineWidth',1, 'Color', [0.9290 0.6940 0.1250]);
    hold on;
    
    % Ajuste de regresión en log–log para obtener exponente, pero graficar en lineal
    p = polyfit(log(topoSizes), log(y), 1);
    yfit = exp(polyval(p, log(topoSizes)));
    p2 = plot(topoSizes, yfit, ':', 'LineWidth',1.5, 'Color', 'Black');
    
    % Etiquetas
    title(algos{i}, 'FontSize',14);
    xlabel('Graph size (nodes)', 'FontSize',12);
   
    %ylabel('Tiempo medio [s]', 'FontSize',10);
    if i == 1
        ylabel('Tiempo medio [s]', 'FontSize',12);
        
        % guardar para la leyenda
        h_analytical = p1;
        h_regression = p2;
    end
    % Ejes lineales (por defecto no hace falta set)
    grid on;
    
    % Anotación de la ley de potencia
    txt = sprintf('F(n)=n^{%.2f}', p(1));
    xlim([min(topoSizes) max(topoSizes)]);
    ylim([min(y)*0.5 max(y)*2]);
    text(0.05, 0.9, txt, 'Units','normalized', 'FontSize',14);
    
    hold off;
end

% Etiquetas de subfigura (opcional)
% subplot(2,2,1), text(0.02,1.05,'a) Spread IDs','Units','normalized','FontSize',11);
% subplot(2,2,2), text(0.02,1.05,'b) MST','Units','normalized','FontSize',11);
% subplot(2,2,3), text(0.02,1.05,'c) PSO','Units','normalized','FontSize',11);
% subplot(2,2,4), text(0.02,1.05,'d) GA','Units','normalized','FontSize',11);


% Leyenda debajo de todos los subplots, centrada
lgd = legend([h_analytical, h_regression], ...
    {'Analytical values', 'Regression function'}, ...
    'Orientation', 'horizontal', ...
    'FontSize', 12);

% Posicionar leyenda centrada abajo usando 'normalized'
lgd.Units = 'normalized';
lgd.Position = [0.40, 0.02, 0.22, 0.05]; % [x, y, width, height]

% Subir todos los subplots un poco para dejar sitio
offset = 0.09;  % más altura para evitar solape
scale = 0.92;   % escalar en altura cada subplot

% Obtener todos los subplots (en orden correcto)
allAxes = findall(gcf, 'Type', 'axes');
allAxes = flipud(allAxes);  % asegurar orden correcto izquierda-derecha

for ax = 1:numel(allAxes)
    allAxes(ax).Position(2) = allAxes(ax).Position(2) + offset;
    allAxes(ax).Position(4) = allAxes(ax).Position(4) * scale;
end

% Exportar la figura a PDF vectorial
exportgraphics(gcf, fullfile(resultsDir,'comparison_4algorithms_linear.pdf'), 'ContentType','vector');

